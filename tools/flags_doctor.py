#!/usr/bin/env python3
"""Доктор флагов — самолекарь флота по канону КАНОН-ФЛАГОВ.json (T27, волна РЕВО 2026-11-19).

КЛАСС БОЛЕЗНИ T27 «флаг ≠ канон при зелёных гейтах»: содержимое тела здорово,
гейты зелёные, а настройки тела разъехались с каноном дома (безопасность выкл,
wiki/projects включены, ветки не чистятся). Дозион такие дыры СМОТРИТ — лечения
у класса не было. Мир решает класс policy-as-code (safe-settings) — дом выводит
своё: канон = явный байт-файл-источник-правды, лечение = идемпотентная машина.

КОНЕЧНЫЙ АВТОМАТ: каждое тело уходит в терминальный вердикт —
  ЗДОРОВ   (все закодированные флаги = канону)
  ВЫЛЕЧЕН  (дельты приведены PATCH'ем, повторной пробой подтверждено)
  ПЛОМБА   (API отказал — код и причина в логе, автоматом не лечится)
  АРХИВ    (архивное тело — только чтение)
Подвешенных состояний нет: пуш <2.0ч (зона §3) отмечается, но флаги живут вне
git-объектов — зона не блокирует лечение настроек (закон §3 охраняет содержание).

ТИШИНА (I0): машина не создаёт issues/комментариев/уведомлений — только API.
ЧЕСТНОСТЬ: каждый PATCH — с HTTP-кодом в лог; отказ = честная ПЛОМБА, ничего
  не подмазывается; числа — из живых проб, никогда руками.
БИЛЛИНГ-ИММУНИТЕТ: stdlib-only, ноль Actions-минут, ноль внешних сервисов.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
HDR = {"Accept": "application/vnd.github+json", "User-Agent": "flags-doctor-dom"}
ZONA_SEK3_H = 2.0  # граница чужой живой волны (закон §3 Дозиона)


def make_req(token):
    hdr = dict(HDR, Authorization=f"Bearer {token}")

    def req(method, path, payload=None, tries=3):
        data = json.dumps(payload).encode() if payload is not None else None
        last = None
        for i in range(tries):
            r = urllib.request.Request(API + path, data=data, method=method)
            for k, v in hdr.items():
                r.add_header(k, v)
            try:
                with urllib.request.urlopen(r, timeout=40) as resp:
                    body = resp.read()
                    return resp.status, (json.loads(body) if body and resp.status != 204 else {})
            except urllib.error.HTTPError as e:
                return e.code, _safe_json(e)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last = e
                time.sleep(2 * (i + 1))  # транзиент сети — ретрай, не падение
        return 0, {"message": f"сеть: {last}"}

    return req


def _safe_json(e):
    try:
        return json.loads(e.read() or b"{}")
    except Exception:
        return {}


def load_canon(path):
    if not os.path.isfile(path):
        sys.exit(f"КАНОН не найден: {path} — честный отказ гадать канон")
    return json.load(open(path, encoding="utf-8"))


def proba(req, full):
    """Живая проба тела: закодированные флаги -> (текущее, канон)."""
    st, d = req("GET", f"/repos/{full}")
    if st != 200:
        return None, f"HTTP {st}: {d.get('message', '?')}"
    ssa = d.get("security_and_analysis") or {}
    cur = {
        "allow_squash_merge": bool(d.get("allow_squash_merge")),
        "delete_branch_on_merge": bool(d.get("delete_branch_on_merge")),
        "secret_scanning": ssa.get("secret_scanning", {}).get("status"),
        "secret_scanning_push_protection": ssa.get("secret_scanning_push_protection", {}).get("status"),
        "has_wiki": bool(d.get("has_wiki")),
        "has_projects": bool(d.get("has_projects")),
    }
    st1, d1 = req("GET", f"/repos/{full}/vulnerability-alerts")
    cur["vulnerability_alerts"] = (st1 == 204) or (st1 == 200 and isinstance(d1, dict) and d1.get("enabled") is True)
    st2, d2 = req("GET", f"/repos/{full}/automated-security-fixes")
    # честная проба: endpoint отвечает и 204, и 200 {"enabled": true} — принимаем оба байта
    cur["automated_security_fixes"] = (st2 == 204) or (st2 == 200 and isinstance(d2, dict) and d2.get("enabled") is True)
    cur["_pushed_at"] = d.get("pushed_at")
    cur["_archived"] = bool(d.get("archived"))
    return cur, None


def deltas(cur, canon):
    flags = canon["закодированные_флаги"]
    out = {}
    for k, want in flags.items():
        have = cur.get(k)
        if k.endswith("_alerts") or k.startswith("automated"):
            want_have = bool(want)
            if have != want_have:
                out[k] = want_have
        elif k in ("secret_scanning", "secret_scanning_push_protection"):
            if have != want:
                out[k] = want
        else:
            if have != bool(want):
                out[k] = bool(want)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="только вердикты (read-only)")
    ap.add_argument("--heal", action="store_true", help="приведение флагов к канону")
    ap.add_argument("--canon", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "КАНОН-ФЛАГОВ.json"))
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--strict", action="store_true", help="--check: exit 1 при дырах")
    args = ap.parse_args()
    if args.check == args.heal:
        sys.exit("одна дверь за прогон: --check ИЛИ --heal")

    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GH_TOKEN не задан — машина не импровизирует")
    canon = load_canon(args.canon)
    req = make_req(token)

    st, repos = req("GET", "/user/repos?per_page=100&sort=pushed")
    if st != 200 or not isinstance(repos, list):
        sys.exit(f"флот не прочитан: HTTP {st}")
    now = datetime.now(timezone.utc)
    rows = []
    for r in repos:
        full = r["full_name"]
        cur, err = proba(req, full)
        if err:
            rows.append({"тело": full, "вердикт": "ПЛОМБА", "причина": err, "дельты": []})
            continue
        if cur["_archived"]:
            rows.append({"тело": full, "вердикт": "АРХИВ", "причина": "только чтение", "дельты": []})
            continue
        dl = deltas(cur, canon)
        age_h = (now - datetime.fromisoformat(cur["_pushed_at"].replace("Z", "+00:00"))).total_seconds() / 3600
        zona = age_h < ZONA_SEK3_H
        if not dl:
            rows.append({"тело": full, "вердикт": "ЗДОРОВ", "причина": "", "дельты": [],
                         "зона_§3": zona})
            continue
        if args.check:
            rows.append({"тело": full, "вердикт": "БОЛЕН", "причина": "", "дельты": sorted(dl),
                         "зона_§3": zona})
            continue
        # --heal: приведение (зона §3 отмечается, но флаги вне git-объектов — лечим)
        patched = {}
        repo_patch = {}
        ssa_p = {}
        for k in sorted(dl):
            if k == "vulnerability_alerts" and dl[k]:
                s, _ = req("PUT", f"/repos/{full}/vulnerability-alerts")
                patched[k] = s
            elif k == "automated_security_fixes" and dl[k]:
                s, _ = req("PUT", f"/repos/{full}/automated-security-fixes")
                patched[k] = s
            elif k in ("secret_scanning", "secret_scanning_push_protection"):
                ssa_p[k] = {"status": dl[k]}
            else:
                repo_patch[k] = dl[k]
        if repo_patch or ssa_p:
            body = dict(repo_patch)
            if ssa_p:
                body["security_and_analysis"] = ssa_p
            s, resp = req("PATCH", f"/repos/{full}", body)
            for k in repo_patch:
                patched[k] = s
            for k in ssa_p:
                patched[k] = s
            if s not in (200,):
                rows.append({"тело": full, "вердикт": "ПЛОМБА",
                             "причина": f"PATCH HTTP {s}: {resp.get('message', '?')}",
                             "дельты": sorted(dl), "зона_§3": zona})
                continue
        # повторная проба: вердикт только по факту байтов
        cur2, err2 = proba(req, full)
        if err2:
            rows.append({"тело": full, "вердикт": "ПЛОМБА", "причина": err2, "дельты": sorted(dl),
                         "зона_§3": zona})
            continue
        dl2 = deltas(cur2, canon)
        rows.append({"тело": full, "вердикт": "ЗДОРОВ" if not dl2 else "ПЛОМБА",
                     "причина": "" if not dl2 else f"не сошлось: {sorted(dl2)}",
                     "дельты": {k: patched.get(k) for k in sorted(dl)}, "зона_§3": zona})
        time.sleep(0.15)

    heals = [r for r in rows if r["вердикт"] == "ВЫЛЕЧЕН"]
    for r in rows:
        if r["вердикт"] == "ЗДОРОВ" and r.get("дельты"):
            r["вердикт"] = "ВЫЛЕЧЕН" if r["дельты"] and all(v == 200 or v == 204 for v in r["дельты"].values()) else r["вердикт"]
    healthy = sum(1 for r in rows if r["вердикт"] == "ЗДОРОВ")
    seals = [r for r in rows if r["вердикт"] == "ПЛОМБА"]
    arch = sum(1 for r in rows if r["вердикт"] == "АРХИВ")
    sick = sum(1 for r in rows if r["вердикт"] == "БОЛЕН")

    print(f"ДОКТОР ФЛАГОВ · канон {canon['имя']} · {now.isoformat(timespec='seconds')}")
    print(f"флот: {len(rows)} · ЗДОРОВ {healthy} · ВЫЛЕЧЕН {len(heals)} · БОЛЕН(check) {sick} · ПЛОМБА {len(seals)} · АРХИВ {arch}")
    for r in rows:
        if r["вердикт"] != "ЗДОРОВ" or r.get("зона_§3"):
            z = " · зона§3" if r.get("зона_§3") else ""
            print(f"  [{r['вердикт']}] {r['тело']}{z} {r['причина'] or r['дельты']}")
    print("закон: факт = байты · вердикт терминален · тишина I0")
    if args.json_out:
        json.dump(rows, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if args.check and args.strict and (sick or seals):
        sys.exit(1)


if __name__ == "__main__":
    main()
