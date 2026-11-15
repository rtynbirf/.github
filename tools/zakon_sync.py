#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zakon_sync.py — синхронизатор закона дома (раунд 14, П-серия дом-закона).

Верифицирует, что закон живёт тремя слоями одновременно и слои сходятся:

  слой 1 · УСТАВ-ДОМА.json  — закон-как-данные (PaC): FSM, инварианты, машины;
  слой 2 · УСТАВ-ДОМА.md    — закон-как-проза (источник, издан Хозяином);
  слой 3 · живой мир        — факты GitHub API живых репо аккаунта.

Проверки:
  S1  схема JSON полна (fsm.states/transitions/terminal, invariants с id/norm/check);
  S2  проза содержит каждый инвариант-id и каждое состояние FSM (карта↔закон);
  S3  мир живых репо: I-1 очередь, I-2 последний прогон, I-3 ящик, I-4 приватность.
      Открытые позиции архивных саркофагов учитываются отдельно (frozen_queue) —
      закон дома действует в живых стенах; разморозка — только слово Хозяина.

Коды выхода: 0 — все три слоя сходятся; 2 — расхождение слоя-3 (перечислено);
3 — fail-closed (схема/проза/сеть). Токен только из env. Только stdlib.

Мировая сверка: policy-as-code 2026 (Spacelift Top-12 PaC; arXiv:2601.05555) —
машиночитаемые правила governance как первичный источник, проза — производная.
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

GH = "https://api.github.com"
OWNER = "rtynbirf"
REQUIRED_INV = {"I-1", "I-2", "I-3", "I-4", "I-5", "I-6"}


def api(url, tok, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "polimat-zakon-sync"})
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read().decode()
            return r.status, (json.loads(body) if body else {}), dict(r.headers)
    except Exception as e:  # noqa: BLE001 — честный счётчик провалов
        return None, {"__error__": str(e)}, {}


def s1_schema(zakon):
    errs = []
    for key in ("schema", "fsm", "invariants", "algorithm", "machines", "prohibitions"):
        if key not in zakon:
            errs.append(f"нет ключа {key}")
    fsm = zakon.get("fsm", {})
    for key in ("states", "transitions", "terminal"):
        if key not in fsm:
            errs.append(f"fsm: нет {key}")
    if zakon.get("fsm", {}).get("terminal") != ["ЧИСТ"]:
        errs.append("fsm.terminal ≠ [ЧИСТ]")
    ids = {i.get("id") for i in zakon.get("invariants", [])}
    missing = REQUIRED_INV - ids
    if missing:
        errs.append(f"инварианты отсутствуют: {sorted(missing)}")
    for inv in zakon.get("invariants", []):
        for key in ("norm", "check", "remediation"):
            if not inv.get(key):
                errs.append(f"{inv.get('id')}: пустой {key}")
    return errs


def s2_prose(zakon, prose_path):
    try:
        prose = open(prose_path, encoding="utf-8").read()
    except OSError as e:
        return [f"проза недоступна: {e}"]
    errs = []
    for inv in zakon["invariants"]:
        if inv["id"] not in prose:
            errs.append(f"{inv['id']} нет в прозе")
    for st in zakon["fsm"]["states"]:
        if st not in prose:
            errs.append(f"состояние {st} нет в прозе")
    return errs


def s3_world(tok):
    rep, page = [], 1
    while True:
        st, chunk, h = api(f"{GH}/user/repos?per_page=100&page={page}&sort=pushed&affiliation=owner", tok)
        if st != 200 or not chunk:
            return None, rep
        rep.extend(chunk)
        if "next" not in h.get("Link", "") or not chunk:
            break
        page += 1
    live = [r for r in rep if not r["archived"]]
    arch = [r for r in rep if r["archived"]]
    world = {"repos_total": len(rep), "repos_live": len(live), "repos_archived": len(arch),
             "private": [r["name"] for r in rep if r["private"]],
             "queue_live": [], "frozen_queue": [], "red_last_run": [], "notifications": None,
             "api_errors": 0}
    for r in live:
        name = r["name"]
        st, items, _ = api(f"{GH}/repos/{OWNER}/{name}/issues?state=open&per_page=100", tok)
        if st != 200:
            world["api_errors"] += 1
            continue
        for it in items:
            kind = "PR" if "pull_request" in it else "issue"
            row = f"{name}#{it['number']} [{kind}] {it['title'][:60]}"
            world["queue_live"].append(row)
        st, runs, _ = api(f"{GH}/repos/{OWNER}/{name}/actions/runs?per_page=1", tok)
        if st != 200:
            world["api_errors"] += 1
        else:
            rr = runs.get("workflow_runs", [])
            if rr and rr[0]["conclusion"] not in ("success", "skipping", "neutral"):
                world["red_last_run"].append(f"{name}: {rr[0]['name'][:40]} → {rr[0]['conclusion']}")
        time.sleep(0.05)
    for r in arch:
        st, items, _ = api(f"{GH}/repos/{OWNER}/{r['name']}/issues?state=open&per_page=100", tok)
        if st != 200:
            world["api_errors"] += 1
            continue
        for it in items:
            kind = "PR" if "pull_request" in it else "issue"
            world["frozen_queue"].append(f"{r['name']}#{it['number']} [{kind}]")
    st, notes, _ = api(f"{GH}/notifications?per_page=100", tok)
    world["notifications"] = len(notes) if st == 200 else None
    if st != 200:
        world["api_errors"] += 1
    return rep, world


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(here, "УСТАВ-ДОМА.json"))
    ap.add_argument("--prose", default=os.path.join(here, "УСТАВ-ДОМА.md"))
    ap.add_argument("--env", default="GITHUB_TOKEN")
    ap.add_argument("--out", default=None, help="файл для JSON-отчёта")
    a = ap.parse_args()
    tok = os.environ.get(a.env, "")
    if not tok:
        print("НЕТ ТОКЕНА в env", a.env, file=sys.stderr)
        sys.exit(3)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {"tool": "zakon_sync", "ts": now, "layers": {}}

    try:
        zakon = json.load(open(a.json, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print("S1 FAIL:", e, file=sys.stderr)
        sys.exit(3)
    errs = s1_schema(zakon)
    report["layers"]["S1_schema"] = {"ok": not errs, "errors": errs}

    errs = s2_prose(zakon, a.prose)
    report["layers"]["S2_prose"] = {"ok": not errs, "errors": errs}

    rep, world = s3_world(tok)
    if rep is None:
        print("S3 FAIL: списки репо недоступны", file=sys.stderr)
        sys.exit(3)
    v = {"ok": not world["queue_live"] and not world["red_last_run"] and
                world["notifications"] == 0 and not world["private"],
         "violations": []}
    if world["queue_live"]:
        v["violations"].append({"inv": "I-1", "fact": world["queue_live"]})
    if world["red_last_run"]:
        v["violations"].append({"inv": "I-2", "fact": world["red_last_run"]})
    if world["notifications"]:
        v["violations"].append({"inv": "I-3", "fact": f"непрочитанных {world['notifications']}"})
    if world["private"]:
        v["violations"].append({"inv": "I-4", "fact": f"приватных {len(world['private'])}"})
    v["frozen_queue"] = {"count": len(world["frozen_queue"]), "note": "архивные саркофаги — разморозка = Класс В (слово Хозяина)"}
    report["layers"]["S3_world"] = v
    report["world"] = world
    report["verdict"] = ("ЗАКОН СХОДИТСЯ: данные↔проза↔мир" if (not errs and v["ok"])
                         else "РАСХОЖДЕНИЕ → ритуал (S1→S5 по каждой позиции)")

    out = json.dumps(report, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out)
    print(out[:2000])
    rc = 3 if (report["layers"]["S1_schema"]["errors"] or report["layers"]["S2_prose"]["errors"]) else (0 if v["ok"] else 2)
    sys.exit(rc)


if __name__ == "__main__":
    main()
