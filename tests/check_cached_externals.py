"""Offline full-resource integration test using previously downloaded, pinned assets.

Cache filenames: OWNER_REPO.tar.gz for archives; original filename for fonts.
Never downloads, executes installers, or applies to the real home.
"""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cache',required=True,type=pathlib.Path)
upstream=parser.parse_args().cache.resolve()
source_root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='dotfiles-full-integration-') as directory:
    root=pathlib.Path(directory)
    repo=root/'repo'; target=root/'target'; target.mkdir()
    shutil.copytree(source_root,repo,ignore=shutil.ignore_patterns('.git','__pycache__','.test-results'))
    lockfile=repo/'home/.chezmoidata/external-lock.json'
    lock=json.loads(lockfile.read_text())
    for item in lock['external_lock']:
        file=upstream/(item['target'] if item['kind']=='font' else item['repo'].replace('/','_')+'.tar.gz')
        assert hashlib.sha256(file.read_bytes()).hexdigest()==item['sha256']
        item['url']=file.as_uri()
    lockfile.write_text(json.dumps(lock))
    config=root/'config.json'
    config.write_text(json.dumps({'data':{'ephemeral':False,'company':False,'homebrew':False,'sudo':False,'email':'','osid':'darwin'}}))
    env=dict(os.environ,HOME=str(target),XDG_CONFIG_HOME=str(root/'config'),XDG_CACHE_HOME=str(root/'cache'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',PYTHONDONTWRITEBYTECODE='1')
    def call(args):
        result=subprocess.run([str(x) for x in args],env=env,capture_output=True,text=True)
        if result.returncode:
            print(result.stdout,result.stderr);raise RuntimeError(args)
        return result.stdout
    call(['git','-C',repo,'init','-b','main'])
    call(['git','-C',repo,'add','.'])
    call(['git','-C',repo,'-c','user.name=Test','-c','user.email=test@example.invalid','-c','commit.gpgsign=false','commit','-m','fixture'])
    opts=['--repo',repo,'--target',target,'--config',config,'--state',root/'state.boltdb','--cache',root/'cache','--profile','full','--component','externals']
    def update(*args):return call([sys.executable,repo/'scripts/dotfiles',*args,*opts])
    call(['chezmoi','--source',repo,'--destination',target,'--config',config,'--persistent-state',root/'state.boltdb','--cache',root/'cache','--override-data',json.dumps({'profile':'full','update_component':'externals'}),'status'])
    update('plan','--plan',root/'plan.json')
    update('apply','--plan',root/'plan.json','--yes')
    update('verify')
    font_directory = 'Library/Fonts' if sys.platform == 'darwin' else '.local/share/fonts'
    for file in ['.oh-my-zsh/oh-my-zsh.sh','.vim_runtime/vimrcs/basic.vim','.vim/bundle/jedi-vim/pythonx/jedi/jedi/__init__.py','.vim/bundle/jedi-vim/pythonx/parso/parso/__init__.py','.config/yazi/plugins/smart-enter.yazi/main.lua',font_directory+'/MesloLGS NF Regular.ttf']:
        assert (target/file).is_file(),file
    assert (target/'.tmux.conf').is_symlink()
    update('plan','--plan',root/'second.json')
    update('apply','--plan',root/'second.json','--yes')
    update('verify')
    print('PASS: all 20 cached upstream resources verified; full temporary plan/apply/verify and repeat passed; Jedi submodules, Yazi plugin and fonts present.')
