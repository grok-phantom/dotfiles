"""Explicit Herdr plugin maintenance; no service restart or configuration apply."""
import json
import os
from pathlib import Path
import re
import shutil

from .common import Stop, run
from . import quicklook

LOCAL_ID = 'dotfiles.quick-actions'
LOCAL_DIR = Path('.config/herdr/plugins/local/dotfiles-quick-actions')
BUILD_TOOLS = {'cloudmanic/herdr-plus': 'go', 'kryptamine/herdr-auto-title': 'go',
               'thanhdat77/herdr-navigator': 'cargo'}


def read_lock(repo):
    entries = []
    for line in (repo/'locks/herdr-plugins.tsv').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        fields = line.split('\t')
        if len(fields) != 3:
            raise Stop('Invalid Herdr lock row')
        source, revision, version = fields
        if (not re.fullmatch(r'[\w.-]+/[\w.-]+', source)
                or not re.fullmatch(r'[a-f0-9]{40}', revision)
                or not re.fullmatch(r'v[0-9][\w.+-]*', version)):
            raise Stop('Invalid Herdr source, commit or release in lock')
        entries.append((source, revision, version))
    sources = [entry[0] for entry in entries]
    if not entries or len(set(sources)) != len(sources):
        raise Stop('Empty or duplicate Herdr lock entries')
    revision = next((rev for src, rev, _ in entries if src == 'dwarvesf/herdr-quicklook'), None)
    if revision != quicklook.REVISION:
        raise Stop('Quicklook lock and reviewed patch revision differ')
    return entries


def inventory():
    value = json.loads(run(['herdr', 'plugin', 'list', '--json'], stage='Herdr inventory'))
    plugins = value['result']['plugins']
    if not isinstance(plugins, list) or any(
            not isinstance(p, dict) or not isinstance(p.get('source', {}), dict)
            for p in plugins):
        raise Stop('Unexpected Herdr inventory format')
    return plugins


def find(plugins, source):
    matches = [p for p in plugins if p.get('source', {}).get('owner', '') + '/' +
               p.get('source', {}).get('repo', '') == source]
    if len(matches) > 1:
        raise Stop('Duplicate installed Herdr source: ' + source)
    return matches[0] if matches else None


def matching(plugin, revision):
    return bool(plugin and plugin.get('enabled') is True
                and plugin.get('source', {}).get('requested_ref') == revision
                and plugin.get('source', {}).get('resolved_commit') == revision)


def local_files(repo, home):
    source = repo/'home/private_dot_config/herdr/plugins/local/dotfiles-quick-actions'
    target = home/LOCAL_DIR
    if not source.is_dir() or not (source/'herdr-plugin.toml').is_file():
        raise Stop('Local Herdr plugin source is missing')
    for path in source.rglob('*'):
        if path.is_file():
            installed = target/path.relative_to(source)
            if not installed.is_file() or installed.read_bytes() != path.read_bytes():
                raise Stop('Local Herdr plugin differs; review/apply its chezmoi configuration first')
    return target


def local_matches(plugins, target):
    matches = [p for p in plugins if p.get('plugin_id') == LOCAL_ID]
    return (len(matches) == 1 and matches[0].get('enabled') is True
            and matches[0].get('source', {}).get('kind') == 'local'
            and Path(matches[0].get('plugin_root', '')).resolve() == target.resolve())


def preflight(repo, home, plugins, entries, install):
    target = local_files(repo, home)
    # A different plugin under our ID must never be silently replaced.
    local = [p for p in plugins if p.get('plugin_id') == LOCAL_ID]
    if local and (len(local) != 1 or local[0].get('source', {}).get('kind') != 'local'
                  or Path(local[0].get('plugin_root', '')).resolve() != target.resolve()):
        raise Stop('Local Herdr plugin ID is already registered to a different source')
    pending = [e for e in entries if not matching(find(plugins, e[0]), e[1])]
    if install:
        missing = sorted({BUILD_TOOLS[src] for src, _, _ in pending
                          if src in BUILD_TOOLS and not shutil.which(BUILD_TOOLS[src])})
        # jq is needed by the local clipboard action, even if all plugins match.
        if not shutil.which('jq'):
            missing.append('jq')
        if missing:
            raise Stop('Missing Herdr dependencies before installation: ' + ', '.join(missing))
    plugin = find(plugins, 'dwarvesf/herdr-quicklook')
    if plugin and plugin.get('source', {}).get('resolved_commit') == quicklook.REVISION:
        quicklook.inspect(plugin)
    return target, pending


def verify(repo, home, entries=None):
    entries = entries or read_lock(repo)
    plugins = inventory()
    target, pending = preflight(repo, home, plugins, entries, install=False)
    failures = [src for src, _, _ in pending]
    if not local_matches(plugins, target):
        failures.append(LOCAL_ID)
    if failures:
        raise Stop('Herdr plugins missing, disabled or at different revisions: ' + ', '.join(failures))
    if not quicklook.inspect(find(plugins, 'dwarvesf/herdr-quicklook'))[2]:
        raise Stop('Quicklook punctuation patch is missing')
    print(f'Verified {len(entries)} pinned plugins, local registration and Quicklook patch.')


def maintain(args):
    if args.action not in ('plan', 'install', 'verify'):
        raise Stop('Herdr plugins support plan, install, verify')
    if not shutil.which('herdr'):
        raise Stop('herdr is not installed')
    entries = read_lock(args.repo)
    if args.action == 'verify':
        verify(args.repo, args.target, entries)
        return
    plugins = inventory()
    target, pending = preflight(args.repo, args.target, plugins, entries, install=True)
    pending_sources = {source for source, _, _ in pending}
    for source, revision, _ in entries:
        print(('install ' if source in pending_sources else 'keep ') +
              source + ' @ ' + revision)
    plugin = find(plugins, 'dwarvesf/herdr-quicklook')
    patch_ready = bool(plugin and plugin.get('source', {}).get('resolved_commit') == quicklook.REVISION
                       and quicklook.inspect(plugin)[2])
    print('Quicklook patch: ' + ('verified' if patch_ready else 'apply after installation and hash check'))
    print('Local plugin: ' + ('registered' if local_matches(plugins, target) else 'link'))
    if args.action == 'plan':
        print('Preflight passed. No downloads, writes or service restarts performed.')
        return
    if not args.yes:
        raise Stop('Herdr plugin installation requires --yes')
    for source, revision, version in pending:
        run(['herdr', 'plugin', 'install', source, '--ref', revision, '--yes'],
            env=dict(os.environ, VERSION=version), stage='Herdr install ' + source,
            diagnostic_output=True)
        if not matching(find(inventory(), source), revision):
            raise Stop('Herdr installation readback failed: ' + source)
    plugins = inventory()
    quicklook.apply(find(plugins, 'dwarvesf/herdr-quicklook'))
    if not local_matches(plugins, target):
        run(['herdr', 'plugin', 'link', target, '--enabled'], stage='Herdr local plugin link')
    verify(args.repo, args.target, entries)
