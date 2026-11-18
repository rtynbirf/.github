#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЗАПЕЧАТЬ СЛЕД: атомарный коммит файлов-фактов в репо через Git Data API.

Родился из факта ×25: account-sentinel 16.11 отработал «зелёным», но снимок
в репо остался от 10.11 — permissions contents:read запрещали PUT, commit_file
молча возвращал False, и доказательство испарялось вместе с раннером.
Здесь отказ ВИДЕН: падение коммита = ненулевой exit code.

Использование: python3 tools/seal_dosezor_trace.py FILE1 [FILE2 ...]
env: GH_TOKEN (или GITHUB_TOKEN), GITHUB_RUN_ID (пометка в сообщении).
"""
import os, sys, json, base64, urllib.request
from datetime import datetime, timezone

REPO_FULL = os.environ.get('REPO_FULL', 'rtynbirf/.github')
TOKEN = (os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN') or '').strip()
if not TOKEN:
    sys.exit('seal: нет GH_TOKEN — след не запечатать')
H = {'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json',
     'Content-Type': 'application/json', 'User-Agent': 'dosezor-seal'}
B = f'https://api.github.com/repos/{REPO_FULL}'


def api(method, url, payload=None):
    req = urllib.request.Request(B + url, headers=H, method=method,
                                 data=json.dumps(payload).encode() if payload is not None else None)
    with urllib.request.urlopen(req, timeout=40) as r:
        body = r.read().decode()
        return json.loads(body) if body else {}


def main():
    files = [f for f in sys.argv[1:] if os.path.exists(f)]
    missing = [f for f in sys.argv[1:] if not os.path.exists(f)]
    if missing:
        print('seal: нет файлов на месте (осмотр падал?) —', ', '.join(missing))
    if not files:
        print('seal: запечатывать нечего')
        return
    changed = []
    for path in files:
        local = open(path, 'rb').read()
        try:
            remote = api('GET', f'/contents/{path}?ref=main')
            if base64.b64decode(remote.get('content', '')) == local:
                print(f'seal: {path} без изменений')
                continue
            # обновление через contents API (файл уже есть — нужен sha)
            data = {'message': f'seal: {path} [skip ci]', 'content': base64.b64encode(local).decode(),
                    'branch': 'main', 'sha': remote['sha']}
            req = urllib.request.Request(f'{B}/contents/{path}', headers=H, method='PUT',
                                         data=json.dumps(data).encode())
            with urllib.request.urlopen(req, timeout=40) as r:
                res = json.load(r)
            print(f'seal: {path} обновлён -> {res["commit"]["sha"][:10]}')
            changed.append(path)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                changed.append(path)  # нового файла нет в репо — идёт в tree ниже
            else:
                sys.exit(f'seal: {path} HTTP {e.code}: {e.read().decode()[:200]}')
    if not changed:
        return
    # новые/пакетные файлы — один атомарный коммит через Git Data API
    ref = api('GET', '/git/ref/heads/main')
    head = ref['object']['sha']
    ref2 = api('GET', '/git/ref/heads/main')['object']['sha']
    if ref2 != head:
        sys.exit('seal: HEAD двинулся — перезапуск с чистого чтения')
    tree_items = []
    for path in changed:
        if path in files:
            blob = api('POST', '/git/blobs', {'content': open(path, 'rb').read().decode('utf-8'),
                                              'encoding': 'utf-8'})
            tree_items.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
    base_tree = api('GET', f'/git/commits/{head}')['tree']['sha']
    tree = api('POST', '/git/trees', {'base_tree': base_tree, 'tree': tree_items})
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    run = os.environ.get('GITHUB_RUN_ID', 'local')
    commit = api('POST', '/git/commits', {
        'message': f'dosezor: запечатан след {now} (run {run}) [skip ci]',
        'tree': tree['sha'], 'parents': [head]})
    api('PATCH', '/git/refs/heads/main', {'sha': commit['sha'], 'force': False})
    print(f'seal: запечатано {changed} -> commit {commit["sha"][:10]}')


main()
