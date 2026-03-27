#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Iterable

ROOT_IGNORE = [
    '.pytest_cache/',
    '**/.pytest_cache/',
    '**/__pycache__/',
    '**/*.pyc',
    '_patch_backup_*/',
    'stage_clean_summary_*.txt',
]

SYSTEM_IGNORE = [
    '.venv/',
    '.venv_broken_*/',
    '.pytest_cache/',
    '**/.pytest_cache/',
    '**/__pycache__/',
    '**/*.pyc',
    '_recovery_backup_*/',
    '_runtime_fix_backup_*/',
    '_core_recover_backup_*/',
    'frontend_build_output_*.txt',
    'frontend_build_summary_*.txt',
    'smoke_workspace_*/',
]

def run(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if proc.returncode != 0:
        msg = 'command failed: ' + ' '.join(args) + '\n' + 'STDOUT:\n' + (proc.stdout or '') + '\n' + 'STDERR:\n' + (proc.stderr or '')
        raise RuntimeError(msg)
    return proc.stdout

def write_ignore(path: Path, lines: Iterable[str]) -> None:
    existing = []
    if path.exists():
        existing = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    keep = []
    in_old_block = False
    for line in existing:
        stripped = line.strip()
        if stripped.startswith('# BEGIN STAGE CLEAN') or stripped == '# Stage hygiene':
            in_old_block = True
            continue
        if in_old_block and stripped.startswith('# END'):
            in_old_block = False
            continue
        if in_old_block:
            continue
        keep.append(line)
    text = '\n'.join([x.rstrip() for x in keep]).rstrip()
    block = ['# Stage hygiene', *lines]
    new_text = (text + '\n\n' if text else '') + '\n'.join(block) + '\n'
    path.write_text(new_text, encoding='utf-8')

def is_protected(path: str) -> bool:
    lower = path.lower()
    return lower.endswith('.md') or lower.endswith('.docx')

def should_untrack(path: str) -> bool:
    if path.startswith('System/.venv/'):
        return True
    if path.startswith('System/.venv_broken_'):
        return True
    if '.pytest_cache/' in path:
        return True
    if '/__pycache__/' in path or path.startswith('__pycache__/'):
        return True
    if path.endswith('.pyc'):
        return True
    if path.startswith('_patch_backup_'):
        return True
    if path.startswith('System/_recovery_backup_'):
        return True
    if path.startswith('System/_runtime_fix_backup_'):
        return True
    if path.startswith('System/_core_recover_backup_'):
        return True
    if path.startswith('System/frontend_build_output_'):
        return True
    if path.startswith('System/frontend_build_summary_'):
        return True
    if path.startswith('System/smoke_workspace_'):
        return True
    return False

def main() -> int:
    parser = argparse.ArgumentParser(description='Stage hygiene cleanup without deleting Word/Markdown files.')
    parser.add_argument('--repo-root', required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not (repo_root / '.git').exists():
        raise SystemExit(f'Not a git repo root: {repo_root}')

    write_ignore(repo_root / '.gitignore', ROOT_IGNORE)
    write_ignore(repo_root / 'System' / '.gitignore', SYSTEM_IGNORE)

    tracked = run(['git', 'ls-files'], cwd=repo_root).splitlines()
    targets = [path for path in tracked if not is_protected(path) and should_untrack(path)]

    for rel in targets:
        run(['git', 'rm', '-r', '--cached', '--ignore-unmatch', '--', rel], cwd=repo_root)

    run(['git', 'add', '.gitignore', 'System/.gitignore'], cwd=repo_root)
    run(['git', 'add', '-A'], cwd=repo_root)

    staged = run(['git', 'diff', '--cached', '--name-status'], cwd=repo_root).splitlines()
    protected_deletes = [line for line in staged if line.startswith('D\t') and is_protected(line.split('\t', 1)[1])]
    if protected_deletes:
        raise RuntimeError('Protected files staged for deletion:\n' + '\n'.join(protected_deletes))

    summary_path = repo_root / 'stage_clean_summary_20260321_final.txt'
    stat = run(['git', 'diff', '--cached', '--stat'], cwd=repo_root)
    summary_lines = [
        f'repo_root: {repo_root}',
        f'untracked_targets: {len(targets)}',
        '',
        'sample_targets:',
        *targets[:50],
        '',
        'git_diff_cached_stat:',
        stat.rstrip(),
    ]
    summary_path.write_text('\n'.join(summary_lines).rstrip() + '\n', encoding='utf-8')
    print(summary_path)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
