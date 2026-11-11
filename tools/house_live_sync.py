#!/usr/bin/env python3
# ⚡ HOUSE-LIVE · автомат реального времени: цифры = территории, а не декларациям.
# Канон: .github/AGENTS.md (аксиома SSOT) · дозор (чужая волна <2ч не трогается) ·
# закон №20/№12 (свои прогоны зелёные по API) · теория конечных автоматов (run доходит до финала).
# stdlib-only. Токен: env LIVE_TOKEN || ACCOUNT_TOKEN || GITHUB_TOKEN.
# Пишет: index/projects.json (refs=HEAD SHA), index/LIVE.json, index/LIVE.md,
#        .github/dosezor/live-ledger.jsonl (append-only), .github/dosezor/live-heartbeat.json.
# Мембранный дозор: активное репо с непустым деревом без мембраны — добивает (лимит 3/прогон).
# Красные на default-ветке: 1 реран транзиента (<24ч, репо не в чужой волне), остальное — долг в LIVE.
import base64, json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

TOK = (os.environ.get("LIVE_TOKEN") or os.environ.get("ACCOUNT_TOKEN")
       or os.environ.get("GITHUB_TOKEN") or "").strip()
OWNER = "rtynbirf"
BASE = "https://api.github.com"
MSK = timezone(timedelta(hours=3))
RUN_ID = os.environ.get("GITHUB_RUN_ID", "0")
DEADLINE = time.time() + 9 * 60
WAVE_HOURS = 2.0          # чужая живая волна
RERUN_MAX_AGE_H = 24.0    # транзиент для рерана
MEMBRANE_LIMIT = 3
MEMBRANE_FILES = ("AGENTS.md", "SECURITY.md", "CODEOWNERS", "LICENSE", ".github/dependabot.yml")
MSGS = {
    "membrane": "docs: мембрана — AGENTS.md для агентов",
    "ssot": "chore(ssot): живая синхронизация refs/статусов (house-live)",
    "live": "chore(live): цифры = территории (house-live)",
    "ledger": "chore(dosezor): живой журнал house-live (append-only)",
}

HDR = {"Accept": "application/vnd.github+json", "User-Agent": "house-live"}
if TOK:
    HDR["Authorization"] = f"token {TOK}"

_calls = 0
def api(path, method="GET", payload=None, _retry=3):
    global _calls
    _calls += 1
    url = path if path.startswith("http") else BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=HDR, method=method)
    for i in range(_retry):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 502) and i < _retry - 1:
                time.sleep(3 * (i + 1)); continue
            return e.code, None
        except Exception:
            if i < _retry - 1:
                time.sleep(2); continue
            return 0, None
    return 0, None

def now_msk():
    return datetime.now(MSK).strftime("%d.%m.%Y %H:%M МСК")

def put_file(repo, path, text, msg):
    """Contents API PUT (идемпотентно: коммит только при изменении байт)."""
    st, cur = api(f"/repos/{OWNER}/{repo}/contents/{path}")
    if st == 200 and isinstance(cur, dict) and "content" in cur:
        if base64.b64decode(cur["content"]).decode() == text:
            return False, None  # без изменений — честная идемпотентность
        sha = cur["sha"]
    else:
        sha = None
    body = {"message": msg, "content": base64.b64encode(text.encode()).decode()}
    if sha:
        body["sha"] = sha
    st, d = api(f"/repos/{OWNER}/{repo}/contents/{path}", "PUT", body)
    if st in (200, 201):
        return True, (d or {}).get("commit", {}).get("sha", "")
    print(f"PUT FAIL {repo}/{path}: {st}", file=sys.stderr)
    return False, None

def get_file(repo, path):
    st, d = api(f"/repos/{OWNER}/{repo}/contents/{path}")
    if st == 200 and isinstance(d, dict) and "content" in d:
        return base64.b64decode(d["content"]).decode()
    return None

def paginate(path):
    out, page = [], 1
    while time.time() < DEADLINE:
        st, chunk = api(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        if st != 200 or not isinstance(chunk, list):
            break
        out += chunk
        if len(chunk) < 100:
            break
        page += 1
    return out

def search_count(q):
    st, d = api(f"/search/issues?q={q}&per_page=1")
    return d.get("total_count", -1) if st == 200 and isinstance(d, dict) else -1

def main():
    verdict_parts, debts = [], []
    # ── 1. Территория ────────────────────────────────────────────────
    repos = paginate("/user/repos?visibility=all&affiliation=owner&sort=pushed")
    active = [r for r in repos if not r["archived"]]
    archived = [r for r in repos if r["archived"]]
    n_pub = sum(1 for r in repos if not r["private"])
    n_priv = sum(1 for r in repos if r["private"])
    issues_open = search_count("user:rtynbirf+is:issue+is:open")
    issues_closed = search_count("user:rtynbirf+is:issue+is:closed")
    prs_open = search_count("user:rtynbirf+is:pr+is:open")
    print(f"территория: {len(repos)} репо · активных {len(active)} · архивных {len(archived)} · публ {n_pub} · прив {n_priv}")
    print(f"issues: открыто {issues_open} / закрыто {issues_closed} · PR открыто {prs_open}")

    # ── 2. Активные репо: SHA, красные, мембрана ─────────────────────
    rows, red_debts, membrane_holes = [], [], []
    for r in active:
        full = r["full_name"]; name = r["name"]
        hours_since_push = (time.time() - datetime.fromisoformat(
            r["pushed_at"].replace("Z", "+00:00")).timestamp()) / 3600.0
        in_wave = hours_since_push < WAVE_HOURS
        st, br = api(f"/repos/{full}/branches/{r['default_branch']}")
        head_sha = ((br or {}).get("commit") or {}).get("sha", "")
        st, tree = api(f"/repos/{full}/git/trees/{r['default_branch']}?recursive=1")
        paths = {t["path"] for t in (tree or {}).get("tree", [])} if st == 200 else set()
        empty_tree = not paths
        have = {f: (f in paths or any(p == f or p.endswith("/" + f) for p in paths)) for f in MEMBRANE_FILES}
        missing = [f for f, ok in have.items() if not ok]
        # красные последние прогоны на default-ветке
        reds, reran = [], 0
        if not empty_tree:
            st, runs = api(f"/repos/{full}/actions/runs?per_page=30")
            if st == 200 and isinstance(runs, dict):
                last = {}
                for run in runs.get("workflow_runs", []):
                    if run["head_branch"] == r["default_branch"] and run["status"] == "completed":
                        last.setdefault(run["name"], run)
                for wf, run in sorted(last.items()):
                    if run["conclusion"] not in ("success", "skipped", None):
                        reds.append({"workflow": wf, "conclusion": run["conclusion"],
                                     "sha": run["head_sha"][:8], "id": run["id"],
                                     "created": run["created_at"]})
                if reds and not in_wave:
                    age_h = (time.time() - datetime.fromisoformat(
                        reds[0]["created"].replace("Z", "+00:00")).timestamp()) / 3600.0
                    if age_h < RERUN_MAX_AGE_H:
                        st2, _ = api(f"/repos/{full}/actions/runs/{reds[0]['id']}/rerun-failed-jobs", "POST")
                        reran = 1 if st2 in (201, 202) else 0
                        if reran:
                            time.sleep(1)
        if missing and not empty_tree:
            membrane_holes.append({"repo": name, "missing": missing})
        if reds:
            tag = "чужая живая волна — не трогаем" if in_wave else ("реран отправлен" if reran else "долг")
            red_debts.append({"repo": name, "reds": reds, "state": tag})
        rows.append({"name": name, "sha": head_sha[:12], "pushed": r["pushed_at"][:16],
                     "empty": empty_tree, "missing": missing, "reds": len(reds),
                     "size_kb": r["size"], "private": r["private"]})

    # ── 3. Мембранный дозор (лимит 3 репо/прогон) ────────────────────
    membrane_fixed = []
    if time.time() < DEADLINE:
        st, canon = api("/repos/rtynbirf/.github/contents/AGENTS.md")
        agents_canon = base64.b64decode(canon["content"]).decode() if st == 200 and canon else ""
        for hole in membrane_holes[:MEMBRANE_LIMIT]:
            name = hole["repo"]
            for f in hole["missing"]:
                if f == "AGENTS.md":
                    text = agents_canon
                elif f == "SECURITY.md":
                    text = f"# Безопасность (канон роя T21)\nВладелец и единственный Хозяин: @{OWNER}.\n\nСообщай уязвимость через Private vulnerability reporting этого репо (или напрямую Хозяину).\n- Реагирование: признание инцидента за 24 часа.\n- Ни один токен/секрет не живёт в репо, логах и артефактах (П-35/П-40).\n"
                elif f == "CODEOWNERS":
                    text = f"# П-20/T21 мембрана: единственный Хозяин роя\n* @{OWNER}\n"
                elif f == "LICENSE":
                    text = "MIT License\n\nCopyright (c) 2026 %s contributors\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the \"Software\"), to deal\nin the Software without restriction, including without limitation the rights\nto use, copy, modify, merge, publish, distribute, sublicense, and/or sell\ncopies of the Software, and to permit persons to whom the Software is\nfurnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all\ncopies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\nFITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\nAUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\nLIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\nOUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\nSOFTWARE.\n" % name
                else:
                    text = 'version: 2\nupdates:\n  - package-ecosystem: "github-actions"\n    directory: "/"\n    schedule:\n      interval: "weekly"\n    groups:\n      actions:\n        patterns:\n          - "*"\n'
                changed, _ = put_file(name, f, text, MSGS["membrane"])
                if changed:
                    membrane_fixed.append(f"{name}/{f}")
                time.sleep(0.4)
    gutted = [r["name"] for r in rows if r["empty"]]
    # после добивки: покрытие = непустые активные минус нечим-покрытые дыры
    fixed_repos = {p.split("/")[0] for p in membrane_fixed}
    holes_left = [h for h in membrane_holes
                  if not all(f"{h['repo']}/{f}" in membrane_fixed for f in h["missing"])]
    mem_total = len([r for r in rows if not r["empty"]])
    mem_covered = mem_total - len(holes_left)

    # ── 4. SSOT-синк: index/projects.json refs = живые HEAD SHA ──────
    ssot_fixed = 0
    pj = get_file("index", "projects.json")
    if pj:
        try:
            reg = json.loads(pj)
            sha_by_full = {f"{OWNER}/{x['name']}": x["sha"] for x in rows}
            size_by_full = {r["full_name"]: r["size"] for r in repos}
            archived_full = {a["full_name"] for a in archived}
            for p in reg.get("projects", []):
                repo_full = p.get("repository", "")
                new_status = "ARCHIVED" if repo_full in archived_full else "ACTIVE"
                new_size = size_by_full.get(repo_full)
                # ref трогаем только у активных (у архивных HEAD неподвижен, чужой волне не мешаем)
                new_ref = sha_by_full.get(repo_full) if repo_full in sha_by_full else None
                drift = (p.get("status") != new_status or p.get("size_kb") != new_size
                         or (new_ref is not None and p.get("ref") != new_ref))
                if drift:
                    p["status"] = new_status
                    if new_size is not None:
                        p["size_kb"] = new_size
                    if new_ref is not None:
                        p["ref"] = new_ref
                    ssot_fixed += 1
            reg["generated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if ssot_fixed:
                changed, _ = put_file("index", "projects.json",
                                      json.dumps(reg, ensure_ascii=False, indent=1) + "\n",
                                      MSGS["ssot"])
                ssot_fixed = ssot_fixed if changed else 0
        except Exception as e:
            debts.append(f"projects.json parse: {e}")

    # ── 5. LIVE.json + LIVE.md в index ───────────────────────────────
    verdict = "ДОМ ЖИВ: цифры = территории" if not red_debts and not membrane_holes else \
              "ДОМ ЖИВ, ДОЛГИ: " + "; ".join(f"{d['repo']}×{len(d['reds'])} ({d['state']})" for d in red_debts)
    live = {
        "schema": 1,
        "generated": datetime.now(MSK).isoformat(),
        "run_id": RUN_ID,
        "counts": {"repos_total": len(repos), "active": len(active), "archived": len(archived),
                    "public": n_pub, "private": n_priv,
                    "issues_open": issues_open, "issues_closed": issues_closed, "prs_open": prs_open},
        "red": red_debts,
        "membrane_holes": membrane_holes,
        "gutted_empty": gutted,
        "verdict": verdict,
    }
    lines = [
        f"# ⚡ LIVE · цифры = территории · пересчёт {now_msk()} · run {RUN_ID}",
        "",
        "| Метрика | Значение |",
        "|---|---|",
        f"| Репозиториев всего | **{len(repos)}** |",
        f"| Активных / архивных | **{len(active)} / {len(archived)}** |",
        f"| Публичных / приватных | **{n_pub} / {n_priv}** |",
        f"| Открытых issues / закрыто за историю | **{issues_open} / {issues_closed}** |",
        f"| Открытых PR | **{prs_open}** |",
        f"| Красные последние прогоны (default-ветки активных) | **{sum(len(d['reds']) for d in red_debts)}** |",
        f"| Мембрана активных (непустые деревья) | **{mem_covered}/{mem_total}** |",
        "",
        f"**Вердикт:** {verdict}",
        "",
    ]
    if red_debts:
        lines.append("## Красные (честные долги)")
        for d in red_debts:
            for x in d["reds"]:
                lines.append(f"- `{d['repo']}` · {x['workflow']} = {x['conclusion']} ({x['sha']}) — {d['state']}")
        lines.append("")
    if gutted:
        lines.append("## Пустые деревья (чистка/Release-миграция, CI не ждём)")
        lines.append(", ".join(f"`{g}`" for g in gutted))
        lines.append("")
    lines.append("_Генерация: `house-live` (крон 30 мин, stdlib). Файл переписывается целиком — история в `dosezor/live-ledger.jsonl` (.github)._")
    live_md = "\n".join(lines) + "\n"
    ch1, sha1 = put_file("index", "LIVE.json", json.dumps(live, ensure_ascii=False, indent=1) + "\n", MSGS["live"])
    ch2, sha2 = put_file("index", "LIVE.md", live_md, MSGS["live"])

    # ── 6. Ledger + heartbeat в .github ──────────────────────────────
    ledger = get_file(".github", "dosezor/live-ledger.jsonl") or ""
    entry = json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "run_id": RUN_ID,
                        "repos": len(repos), "active": len(active), "archived": len(archived),
                        "public": n_pub, "private": n_priv,
                        "issues_open": issues_open, "prs_open": prs_open,
                        "red": [d["repo"] for d in red_debts],
                        "membrane_fixed": membrane_fixed, "ssot_refs_fixed": ssot_fixed,
                        "live_changed": bool(ch1 or ch2), "membrane_covered": f"{mem_covered}/{mem_total}", "verdict": verdict},
                       ensure_ascii=False)
    new_ledger = (ledger + entry + "\n") if ledger else (entry + "\n")
    ch3, sha3 = put_file(".github", "dosezor/live-ledger.jsonl", new_ledger, MSGS["ledger"])
    put_file(".github", "dosezor/live-heartbeat.json",
             json.dumps({"beat": datetime.now(timezone.utc).isoformat(), "run_id": RUN_ID,
                         "verdict": verdict}, ensure_ascii=False, indent=1) + "\n",
             MSGS["ledger"])

    # ── 7. Финал (конечный автомат: состояние ДОМ_ЧИСТ/ПЕРЕДАЛ) ──────
    print(f"SSOT refs исправлено: {ssot_fixed}")
    print(f"мембрана добавлена: {membrane_fixed or 'ничего'}")
    print(f"LIVE.md/json изменены: {ch1 or ch2} · ledger: {ch3}")
    print(f"красные: {[(d['repo'], d['state']) for d in red_debts] or 'нет'}")
    print(f"вызовов API: {_calls}")
    print("ВЕРДИКТ:", verdict)

if __name__ == "__main__":
    main()
