#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МИНУТНЫЙ ГРОССБУХ: кто съел минуты Actions аккаунта за последние N дней.

ПЛОМБА-2026-11-10: ноябрь Linux 7247.67 ед. при лимите 2000 мин/мес — вот
источник заморозки приватного CI. Но ДО гроссбуха не существовало: ни у
GitHub, ни у дома не было разбивки «сколько съело каждое репо».

Методология (честная):
  - длительность прогона ≈ updated_at - run_started_at (точка отсчёта —
    старт джоб, очередь исключена);
  - округление вверх до целой минуты на прогон (GitHub считает так);
  - множители стандартных раннеров: linux ×1, windows ×2, macos ×10;
  - список прогонов ОС раннера не отдаёт, поэтому считаем linux ×1 —
    консервативный НИЖНИЙ предел (честно помечено в отчёте).
"""
import os, json, math, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

TOKEN = os.environ.get('GH_TOKEN') or open('/home/z/my-project/scripts/.token_active').read().strip()
H = {'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json',
     'User-Agent': 'hive-minutes-ledger'}
DAYS = int(os.environ.get('LEDGER_DAYS', '30'))
MAX_PAGES = 8


def api(url):
    req = urllib.request.Request(url, headers=H)
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception as e:
            if a == 3:
                return {'_error': str(e)}
            time.sleep(2 * (a + 1))


def iso(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def main():
    since = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime('%Y-%m-%d')
    repos = api('https://api.github.com/user/repos?per_page=100&sort=pushed&affiliation=owner')
    rows = []
    for r in repos:
        if r['fork'] or r['archived']:
            continue
        name, total_min, n_runs, red = r['name'], 0, 0, 0
        for page in range(1, MAX_PAGES + 1):
            d = api(f"https://api.github.com/repos/rtynbirf/{name}/actions/runs"
                    f"?per_page=100&page={page}&created=>{since}")
            runs = d.get('workflow_runs', [])
            if d.get('_error') or not runs:
                if d.get('_error'):
                    red += 1
                break
            for run in runs:
                if run.get('run_started_at') and run.get('updated_at'):
                    mins = (iso(run['updated_at']) - iso(run['run_started_at'])).total_seconds() / 60
                    # потолок 360 мин = платформенный максимум джобы: прогоны,
                    # висевшие в очереди при заморозке квоты (ПЛОМБА), получают
                    # фиктивную «длительность» вплоть до дней — ограничиваем.
                    mins = min(mins, 360)
                    if mins > 0:
                        total_min += math.ceil(mins)
                        n_runs += 1
            if len(runs) < 100:
                break
            time.sleep(0.2)
        rows.append({'repo': name, 'minutes_linux_x1': total_min, 'runs': n_runs, 'page_errors': red})

    rows.sort(key=lambda x: -x['minutes_linux_x1'])
    total = sum(x['minutes_linux_x1'] for x in rows)
    top = rows[:12]

    md = [f"# МИНУТНЫЙ ГРОССБУХ · {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
          "",
          f"Период: последние **{DAYS}** дней (с {since}) · Методология: длительность прогона "
          f"(`updated_at − run_started_at`), потолок **360 мин/прогон** (платформенный максимум джобы — "
          f"прогоны, висевшие в очереди при заморозке квоты, иначе дают фиктивные дни), множитель linux ×1 "
          f"(ОС раннера в списке прогонов не отдаётся → это НИЖНИЙ предел; windows ×2 / macos ×10 не учтены).",
          "",
          f"**ИТОГО по флоту: ≈{total} мин ×linux** за {DAYS} дней "
          f"(≈{total / DAYS:.0f} мин/день; лимит аккаунта 2000 мин/мес ≈ 66 мин/день на платной квоте приватных).",
          "",
          "| # | Репо | Минут (linux ×1) | Прогонов |",
          "| --- | --- | --- | --- |"]
    for i, x in enumerate(top, 1):
        md.append(f"| {i} | {x['repo']} | {x['minutes_linux_x1']} | {x['runs']} |")
    md.append("")
    others = sum(x['minutes_linux_x1'] for x in rows[12:])
    md.append(f"| — | остальные {len(rows) - 12} репо | {others} | — |" if len(rows) > 12 else "")
    md.append("")
    md.append("_Весь флот на 2026-11-18 публичен → текущее потребление бесплатной квоты = 0; "
              "гроссбух показывает источники ноябрьского удара (7247.67 ед.) и включается в "
              "задел на любой будущий приватный период._")

    out_md = '\n'.join(x for x in md if x is not None)
    out_json = {'generated': datetime.now(timezone.utc).isoformat(), 'days': DAYS,
                'total_minutes_linux_x1': total, 'repos': rows}
    if len(sys.argv) > 1:
        open(sys.argv[1], 'w').write(out_md)
    if len(sys.argv) > 2:
        json.dump(out_json, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
    print(out_md[:1200])
    print('...')
    print(f"TOTAL {total} min / {sum(x['runs'] for x in rows)} runs / {len(rows)} repos")


main()
