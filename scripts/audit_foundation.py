"""Read-only foundation inventory. No remote access and no project mutations."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote


def git_state(folder):
    executable = shutil.which('git')
    if not executable:
        return {'status': 'git_unavailable'}
    env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}

    def run(*args):
        return subprocess.run(
            [executable, '-C', str(folder), *args], capture_output=True,
            encoding='utf-8', errors='replace', timeout=15, env=env)

    try:
        top = run('rev-parse', '--show-toplevel')
        if top.returncode:
            if 'not a git repository' in top.stderr:
                return {'status': 'not_a_repository'}
            return {'status': 'git_check_failed'}
        result = {'status': 'repository', 'top_level': top.stdout.strip(),
                  'git_marker': 'file' if (folder / '.git').is_file() else
                  'directory' if (folder / '.git').is_dir() else 'ancestor'}
        for key, args in {
            'branch': ('branch', '--show-current'),
            'head': ('rev-parse', '--verify', 'HEAD'),
            'common_dir': ('rev-parse', '--git-common-dir'),
            'changes': ('status', '--porcelain=v1', '--untracked-files=normal'),
            'worktrees': ('worktree', 'list', '--porcelain'),
        }.items():
            response = run(*args)
            result[key] = response.stdout.strip() if response.returncode == 0 else None
            if response.returncode and key != 'head':
                result.setdefault('checks_failed', []).append(key)
        return result
    except (OSError, subprocess.TimeoutExpired):
        return {'status': 'git_check_failed'}


def audit(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Project directory does not exist')
    expected = ['README.md', 'AGENTS.md', 'docs/facts', 'docs/Spec',
                'docs/工程规则.md', 'src']
    report = {
        'root': str(root),
        'layout_suggestions': {p: (root / p).exists() for p in expected},
        'git': {'root': git_state(root)},
        'broken_local_links': [], 'unreadable_documents': [],
        'skipped_documents': [], 'documents_checked': 0,
        'limits': ['Suggested paths are not mandatory for existing projects.',
                   'No link anchors, reference-style links, external URLs or business behavior verified.',
                   'No source relocation, remote access, secret scan or deployment-trigger audit performed.'],
    }
    if (root / 'src').is_dir():
        report['git']['src'] = git_state(root / 'src')
    documents = [p for p in (root / 'README.md', root / 'AGENTS.md') if p.is_file()]
    docs = root / 'docs'
    if docs.is_dir() and not docs.is_symlink():
        for folder, dirs, names in os.walk(docs, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in ('.git', 'node_modules')
                             and not (Path(folder) / d).is_symlink())
            documents.extend(Path(folder) / n for n in sorted(names) if n.endswith('.md'))
            if len(documents) > 300:
                report['limits'].append('Document scan capped at 300 files.')
                documents = documents[:300]
                break
    for path in documents:
        name = path.relative_to(root).as_posix()
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            report['skipped_documents'].append(name)
            continue
        try:
            if path.stat().st_size > 1_000_000:
                report['skipped_documents'].append(name)
                continue
            text = path.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError):
            report['unreadable_documents'].append(name)
            continue
        report['documents_checked'] += 1
        text = re.sub(r'(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$', '', text)
        for match in re.finditer(r'\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)', text):
            target = match.group(1).strip('<>')
            if target.startswith('#') or re.match(r'^[a-zA-Z][\w+.-]*:', target) or target.startswith('//'):
                continue
            target_path = unquote(target.split('#', 1)[0].split('?', 1)[0])
            if target_path and not (path.parent / target_path).exists():
                report['broken_local_links'].append({'document': name, 'target': target})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    args = parser.parse_args()
    try:
        report = audit(args.project)
    except (OSError, ValueError) as error:
        parser.exit(2, str(error) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # A successful inventory is not a completed foundation or product acceptance.
    return 1 if report['broken_local_links'] or report['unreadable_documents'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
