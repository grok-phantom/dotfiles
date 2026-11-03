"""Keep repository maintenance documentation links valid without network access."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def prose(path):
    # Paths in fenced examples describe user projects, not necessarily this repo.
    return re.sub(r'(?ms)^\s*(```|~~~).*?^\s*\1[^\n]*$', '', path.read_text())


def anchors(path):
    seen, result = {}, set()
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', prose(path), re.M):
        slug = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
        count = seen.get(slug, 0)
        result.add(slug + (f'-{count}' if count else ''))
        seen[slug] = count + 1
    return result


class DocumentationLinks(unittest.TestCase):
    def test_maintenance_document_local_links_and_anchors(self):
        files = [ROOT/'README.md', ROOT/'AGENTS.md', ROOT/'locks/README.md', *sorted((ROOT/'docs').glob('*.md'))]
        problems = []
        for path in files:
            for link in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', prose(path)):
                if re.match(r'[a-zA-Z][\w+.-]*:', link) or link.startswith('/'):
                    continue
                target, _, fragment = unquote(link).partition('#')
                resolved = path.parent/target if target else path
                if not resolved.exists():
                    problems.append(f'{path.relative_to(ROOT)}: missing {link}')
                elif fragment and resolved.suffix == '.md' and fragment not in anchors(resolved):
                    problems.append(f'{path.relative_to(ROOT)}: missing anchor {link}')
        self.assertEqual(problems, [])
