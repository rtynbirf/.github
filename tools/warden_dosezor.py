#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛡 ДОЗОР ДОЗОРА — волна ×25. Следит за самими дозорами и печатью дома.

Родился из факта: 2026-11-10 хаб дозоров (github-runbook, 22 workflow) замолчал,
и 8 дней НИКТО не заметил — у дозоров не было собственного дозора.
2026-11-18 дом запечатан: 30 репо archived (в т.ч. реестр #10, hub, nous),
комменты в реестре закрыты платформой. Дозор живёт в живом штабе .github,
работает даже при исчерпанных минутах приватных репо (канон account-sentinel).

Проверяет (только репорт; лечение не выполняет — закон ревизора):
  1) ПЕЧАТЬ: набор archived-репо против dosezor/warden-seal-baseline.json.
     Вскрытие печати или неожиданная печать = ALARM + обновление baseline
     (аларм звучит один раз, GitOps-реконсиляция).
  2) ЖИВЫЕ ОРГАНЫ .github: канон workflow обязаны быть state=active.
  3) СНИМКИ: dosezor/account-sentinel-latest.json свежее порога (неделя+люфт).
  4) СЛЕДЫ РЕЕСТРА #10: последние СЧЁТЧИК/РЕВИЗОР/OSPS — исторический факт
     (реестр запечатан 2026-11-18; возраст растёт легально, не аларм).

Результат: dosezor/warden-latest.json (факт) + ALARM-issue при дивергенции
(дедуп по WARDEN-FP среди OPEN). Зелёный — тихо. post_full=1 — полный
статус-issue даже при зелёном. Снимок коммитится с [skip ci].
"""
import os, json, subprocess, urllib.request
from datetime import datetime, timezone

OWNER = 'rtynbirf'
REPO = f'{OWNER}/.github'
CANON_ACTIVE = ['account-sentinel.yml', 'house-live.yml', 'house-sweep.yml',
                'revo-account.yml', 'revo-obhod.yml', 'scorecard-analysis.yml',
                'zizmor.yml', 'ci.yml', 'dosezor-warden.yml']
KNOWN_DISABLED = ['account-facade.yml', 'facade-birth.yml', 'self-heal.yml']
SENTINEL_STALE_DAYS = 8          # еженедельник + люфт
FOOTPRINTS = {                   # след реестра #10 -> маркеры (исторический факт)
    'СЧЁТЧИК': ['СЧЁТЧИК ПЕРЕСЧИТАН'],
    'РЕВИЗОР': ['AUDITOR-FP'],
    'OSPS': ['OSPS-FP'],
}
REGISTRY = 'github-runbook'
REGISTRY_ISSUE = 10

TOKEN = (os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
         or open('/home/z/my-project/scripts/.token_active').read().strip())
H = {'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json',
     'User-Agent': 'dosezor-warden'}


def api(url):
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def iso(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def main():
    now = datetime.now(timezone.utc)
    alarms = []

    # ── 1) ПЕЧАТЬ: набор archived-репо против baseline ──────────────────────
    base_path = 'dosezor/warden-seal-baseline.json'
    baseline = None
    if os.path.exists(base_path):
        baseline = json.load(open(base_path))
    repos = api(f'https://api.github.com/users/{OWNER}/repos?per_page=100&sort=pushed&affiliation=owner')
    repos += api(f'https://api.github.com/users/{OWNER}/repos?per_page=100&sort=pushed&affiliation=owner&page=2') \
        if len(repos) >= 100 else []
    sealed = sorted(r['name'] for r in repos if r['archived'] and not r['fork'])
    live = sorted(r['name'] for r in repos if not r['archived'] and not r['fork'])
    seal_diff = {}
    if baseline is None:
        seal_note = 'baseline создан впервые (без аларма)'
    else:
        unsealed = sorted(set(baseline['sealed']) - set(sealed))       # вскрытие печати
        new_sealed = sorted(set(sealed) - set(baseline['sealed']))     # неожиданная печать
        seal_diff = {'unsealed': unsealed, 'newly_sealed': new_sealed}
        if unsealed:
            alarms.append('ВСКРЫТА ПЕЧАТЬ (стало live): ' + ', '.join(unsealed))
        if new_sealed:
            alarms.append('НОВАЯ ПЕЧАТЬ (стало archived): ' + ', '.join(new_sealed))
        seal_note = f'сверено с baseline от {baseline["generated"][:10]}'
    os.makedirs('dosezor', exist_ok=True)
    json.dump({'generated': now.isoformat(), 'sealed': sealed, 'live': live},
              open(base_path, 'w'), ensure_ascii=False, indent=1)

    # ── 2) ЖИВЫЕ ОРГАНЫ .github ──────────────────────────────────────────────
    wfs = api(f'https://api.github.com/repos/{REPO}/actions/workflows?per_page=100')
    states = {w['path'].split('/')[-1]: w['state'] for w in wfs.get('workflows', [])}
    canon = {}
    for name in CANON_ACTIVE:
        st = states.get(name, 'ОТСУТСТВУЕТ')
        canon[name] = st
        if st != 'active' and name not in KNOWN_DISABLED:
            alarms.append(f'живой орган .github/{name} в состоянии `{st}`')

    # ── 3) СНИМКИ dosezor/ ───────────────────────────────────────────────────
    import base64 as _b64
    snaps = {}
    try:
        sj = api(f'https://api.github.com/repos/{REPO}/contents/dosezor/account-sentinel-latest.json')
        raw_json = json.loads(_b64.b64decode(sj['content']).decode())
        gen = iso(raw_json['generated'])
        age = (now - gen).total_seconds() / 86400
        snaps['account-sentinel-latest.json'] = {'generated': gen.isoformat(), 'age_days': round(age, 2)}
        if age > SENTINEL_STALE_DAYS:
            alarms.append(f'account-sentinel снимок устарел: {age:.1f} дн (порог {SENTINEL_STALE_DAYS})')
    except Exception as e:
        snaps['account-sentinel-latest.json'] = {'error': type(e).__name__}
        alarms.append(f'account-sentinel снимок недоступен: {type(e).__name__}')

    # ── 4) СЛЕДЫ РЕЕСТРА #10 (исторический факт, не аларм) ──────────────────
    footprints = {}
    try:
        comments = api(f'https://api.github.com/repos/{OWNER}/{REGISTRY}/issues/{REGISTRY_ISSUE}/comments?per_page=100&page=1')
        for tag, markers in FOOTPRINTS.items():
            best = None
            for c in comments:
                if any(m in c.get('body', '') for m in markers):
                    dt = iso(c['created_at'])
                    if best is None or dt > best[0]:
                        best = (dt, c['html_url'])
            footprints[tag] = {'last': best[0].isoformat(), 'url': best[1]} if best else {'last': None}
    except Exception as e:
        footprints['error'] = type(e).__name__

    verdict = f'🚨 ДИВЕРГЕНЦИЙ: {len(alarms)}' if alarms else '🟢 КАНОН, ПЕЧАТЬ И СНИМКИ ЗДОРОВЫ'
    gh = os.environ
    run_url = (f"{gh.get('GITHUB_SERVER_URL', 'https://github.com')}/{gh.get('GITHUB_REPOSITORY', REPO)}"
               f"/actions/runs/{gh.get('GITHUB_RUN_ID', '')}")
    import hashlib
    fp = hashlib.sha256(('|'.join(sorted(alarms)) or 'green').encode()).hexdigest()[:16]

    snapshot = {
        'generated': now.isoformat(),
        'run_id': gh.get('GITHUB_RUN_ID', 'local'),
        'run_url': run_url,
        'mode': 'dispatch-post_full' if gh.get('POST_FULL', '').strip().lower() in ('1', 'true') else
                ('dispatch' if gh.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' else 'schedule'),
        'verdict': verdict,
        'alarms': alarms,
        'seal': {'sealed': len(sealed), 'live': len(live), 'note': seal_note, 'diff': seal_diff},
        'canon_workflows': canon,
        'snapshots': snaps,
        'registry10_footprints': footprints,
        'fingerprint': fp,
    }
    os.makedirs('dosezor', exist_ok=True)
    json.dump(snapshot, open('dosezor/warden-latest.json', 'w'), ensure_ascii=False, indent=1)
    print('ВЕРДИКТ:', verdict)
    for a in alarms:
        print('  🚨', a)

    # ── ALARM-issue (дедуп по WARDEN-FP среди OPEN) ──────────────────────────
    if alarms or gh.get('POST_FULL', '').strip().lower() in ('1', 'true'):
        issues = api(f'https://api.github.com/repos/{REPO}/issues?state=open&per_page=50')
        dup = next((i for i in issues if f'WARDEN-FP:{fp}' in (i.get('body') or '')), None)
        if dup:
            print('АЛАРМ УЖЕ ОТКРЫТ (дедуп):', dup['html_url'])
        else:
            body = (
                f"🛡 **ДОЗОР ДОЗОРА** · {now.strftime('%Y-%m-%d %H:%M UTC')} · {verdict}\n\n"
                f"**Печать дома:** запечатано {len(sealed)} · живых {len(live)} · {seal_note}\n\n"
                + (f"**Алармы:**\n" + '\n'.join(f'- 🚨 {a}' for a in alarms) + '\n\n' if alarms else '')
                + f"Снимок факта: `dosezor/warden-latest.json` · "
                  f"[запуск {gh.get('GITHUB_RUN_ID', 'local')}]({run_url}) · "
                  f"Только репорт, лечение не выполняет (закон ревизора)\n\n"
                  f"<!-- WARDEN-FP:{fp} -->")
            req = urllib.request.Request(
                f'https://api.github.com/repos/{REPO}/issues',
                data=json.dumps({'title': f"ALARM: дозор дозора — {verdict}" if alarms
                                 else "🛡 ДОЗОР ДОЗОРА · полный статус (dispatch)",
                                 'body': body}).encode(),
                headers={**H, 'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=30) as r:
                iss = json.load(r)
            print('ISSUE:', iss['html_url'])

    # ── приведено в соответствие: закрыть свои отработавшие ALARM-issue ──────
    if not alarms and gh.get('POST_FULL', '').strip().lower() not in ('1', 'true'):
        try:
            issues = api(f'https://api.github.com/repos/{REPO}/issues?state=open&per_page=50')
            for i in issues:
                if 'WARDEN-FP:' in (i.get('body') or ''):
                    req = urllib.request.Request(
                        f"https://api.github.com/repos/{REPO}/issues/{i['number']}",
                        data=json.dumps({'state': 'closed',
                                         'state_reason': 'completed'}).encode(),
                        headers={**H, 'Content-Type': 'application/json'}, method='PATCH')
                    with urllib.request.urlopen(req, timeout=30) as r:
                        r.read()
                    print(f"ALARM #{i['number']} приведён в соответствие — закрыт дозором")
        except Exception as e:
            print('auto-close пропущен:', type(e).__name__)

    # ── коммит факта (через seal — отказ виден, [skip ci]) ───────────────────
    if gh.get('GITHUB_RUN_ID'):  # в Actions
        import subprocess
        r = subprocess.run(['python3', 'tools/seal_dosezor_trace.py',
                            'dosezor/warden-latest.json', base_path])
        if r.returncode != 0:
            print('SEAL FAILED — след не запечатан, аларм-коммит не приземлился')


def base64_decode(s):
    import base64
    return base64.b64decode(s).decode()


main()
