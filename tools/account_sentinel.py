#!/usr/bin/env python3
# 🛡 ДОЗИОР АККАУНТА · живой еженедельный осмотр флота (T24 + T25 + Э-2.4)
# Канон: repo-doctrine (чек-лист 01, 21-гигиена) · github-runbook#10 (закон §3: чужие
# живые волны не трогать) · закон закрытия (issue закрывается живым зелёным прогоном).
# Биллинг-иммунитет: живёт в ПУБЛИЧНОМ .github — работает при исчерпанных минутах приватных.
# Приватность: приватный срез — ТОЛЬКО агрегаты (мембрана: ни имён, ни путей публично).
# Вердикт = только ДЫРЫ (механика канона). T24/T25/PR = наблюдения (не красят вердикт).
# Репо в чужой живой волне (пуш <2ч) — исключены из вердикта, помечены отдельно.
# stdlib-only. Токен: env SENTINEL_TOKEN.
import json, os, re, sys, time, base64, urllib.request, urllib.error
from datetime import datetime, timezone

TOKEN = os.environ.get("SENTINEL_TOKEN", "").strip()
OWNER = "rtynbirf"
BASE = "https://api.github.com"
SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY")
RUN_ID = os.environ.get("GITHUB_RUN_ID", "0")
DEADLINE = time.time() + 8 * 60
ACTIVE_HOURS = 2.0  # чужая живая волна: пуш свежее N часов

WIKI_KEEP = {"karaoke-dream", "singulyar-llm", "rtynbirf.github.io", "universal-agent", "markitdown"}
USE_RE = re.compile(r"uses:\s*([^\s'\"#]+)")
SHA_RE = re.compile(r"@[0-9a-f]{40}\b")
DEP_UPDATE_RE = re.compile(r"\S+ in \S+ for ")  # «github_actions in / for … - Update»

def api(path, method="GET", data=None, _retry=2):
    req = urllib.request.Request(BASE + path, method=method)
    if TOKEN:
        req.add_header("Authorization", f"token {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    body = json.dumps(data).encode() if data is not None else None
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, body, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        if e.code == 403 and _retry > 0 and e.headers.get("X-RateLimit-Remaining") == "0":
            time.sleep(min(int(e.headers.get("Retry-After", "30")), 60))
            return api(path, method, data, _retry - 1)
        try:
            return e.code, json.loads(e.read() or b"null")
        except Exception:
            return e.code, None
    except Exception as e:
        return -1, {"message": str(e)[:80]}

def sweep_repo(full, priv, hours_since_push):
    h = {"repo": full, "holes": [], "notes": [], "info": {}}
    h["active_wave"] = (hours_since_push is not None and hours_since_push < ACTIVE_HOURS)
    st, cur = api(f"/repos/{full}")
    if st != 200:
        h["holes"].append(f"GET-репо {st}")
        return h
    db = cur["default_branch"]
    canon = {"allow_squash_merge": True, "allow_rebase_merge": False,
             "delete_branch_on_merge": True, "allow_auto_merge": True,
             "allow_update_branch": True, "use_squash_pr_title_as_default": True}
    for k, v in canon.items():
        if cur.get(k) != v:
            h["holes"].append(f"флаг {k}≠канон")
    if not cur.get("description"):
        h["holes"].append("нет description")
    t = len(cur.get("topics") or [])
    if not (5 <= t <= 15):
        h["holes"].append(f"topics={t} (канон 5–15)")
    if cur.get("has_projects"):
        h["holes"].append("projects включён")
    if cur.get("has_discussions"):
        h["holes"].append("discussions включён")
    if cur.get("has_wiki") and full.split("/")[1] not in WIKI_KEEP:
        h["holes"].append("wiki включён")
    if not priv:
        sa = cur.get("security_and_analysis") or {}
        for key, label in [("secret_scanning", "secret scanning"),
                           ("secret_scanning_push_protection", "push protection")]:
            if (sa.get(key) or {}).get("status") != "enabled":
                h["holes"].append(f"{label} выкл")
        st, _ = api(f"/repos/{full}/vulnerability-alerts")
        if st not in (200, 204): h["holes"].append("dependabot-алерты выкл")
        st, _ = api(f"/repos/{full}/automated-security-fixes")
        if st not in (200, 204): h["holes"].append("автофиксы выкл")
        st, _ = api(f"/repos/{full}/branches/{db}/protection")
        if st != 200: h["holes"].append("main не защищён")
    st, prs = api(f"/repos/{full}/pulls?state=open&per_page=100")
    n = len(prs) if isinstance(prs, list) else 0
    if n:
        h["notes"].append(f"PR открытых: {n}: " +
                          "; ".join(f"#{p['number']} {p['title'][:50]}" for p in prs[:5]))
    st, runs = api(f"/repos/{full}/actions/runs?per_page=3")
    wr = (runs or {}).get("workflow_runs") if isinstance(runs, dict) else None
    if wr:
        last = wr[0]
        if last["conclusion"] == "failure":
            name = last["name"]
            if priv:
                st, jobs = api(last["jobs_url"])
                if (jobs or {}).get("total_count") == 0:
                    h["info"]["billing"] = True  # не красный маяк: биллинг-стена
                else:
                    h["holes"].append(f"красный прогон: {name}")
            elif DEP_UPDATE_RE.search(name) or "Update #" in name:
                h["notes"].append(f"dependabot-прогон красный (не маяк): {name}")
            else:
                h["holes"].append(f"красный прогон: {name}")
    if time.time() > DEADLINE:
        h["info"]["sweep_truncated"] = True
        return h
    st, wf = api(f"/repos/{full}/contents/.github/workflows?ref={db}")
    if isinstance(wf, list) and wf:
        total = unpinned = 0
        for f in wf:
            if not f["name"].endswith((".yml", ".yaml")):
                continue
            st2, blob = api(f"/repos/{full}/contents/{f['path']}?ref={db}")
            if st2 != 200 or not isinstance(blob, dict):
                continue
            text = base64.b64decode(blob.get("content", "")).decode("utf-8", "replace")
            for m in USE_RE.finditer(text):
                total += 1
                if not SHA_RE.search(m.group(1)):
                    unpinned += 1
        if total:
            if unpinned:
                h["notes"].append(f"T24: {unpinned}/{total} uses без SHA-пина")
            else:
                h["info"]["pins_ok"] = True
    st, tree = api(f"/repos/{full}/git/trees/{db}?recursive=1")
    if isinstance(tree, dict) and tree.get("tree"):
        z = [e["path"] for e in tree["tree"]
             if e.get("type") == "blob" and e.get("size", 1) == 0
             and os.path.basename(e["path"]) not in (".gitkeep", ".keep")]
        if z:
            h["notes"].append(f"T25: {len(z)} пустых файлов: " + ", ".join(p.split('/')[-1] for p in z[:5]))
    return h

def commit_file(full, path, text, branch, msg):
    st, old = api(f"/repos/{full}/contents/{path}?ref={branch}")
    sha = old["sha"] if isinstance(old, dict) and old.get("sha") else None
    data = {"message": msg, "content": base64.b64encode(text.encode()).decode(), "branch": branch}
    if sha:
        data["sha"] = sha
    st, _ = api(f"/repos/{full}/contents/{path}", "PUT", data)
    return st in (200, 201)

def upsert_issue(full, title, body, marker):
    st, issues = api(f"/repos/{full}/issues?state=open&per_page=100")
    target = None
    for i in (issues or []):
        if i.get("title", "").startswith(marker):
            target = i["number"]; break
    if target:
        st, _ = api(f"/repos/{full}/issues/{target}", "PATCH", {"body": body})
        return target, st
    st, ni = api(f"/repos/{full}/issues", "POST", {"title": title, "body": body,
                                                   "labels": ["automated", "dosezor"]})
    return (ni or {}).get("number"), st

def main():
    now = datetime.now(timezone.utc)
    st, repos = api("/user/repos?per_page=100&sort=full_name&affiliation=owner")
    if st != 200:
        sys.exit(f"API {st}: флот не прочитан")
    pub, active, priv_billing, priv_prs, priv_holes = [], [], 0, 0, 0
    for r in repos:
        if r["archived"]:
            continue
        try:
            pt = datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
            hrs = (now - pt).total_seconds() / 3600
        except Exception:
            hrs = None
        if r["private"]:
            pr = sweep_repo(r["full_name"], True, hrs)
            priv_billing += 1 if pr["info"].get("billing") else 0
            priv_prs += ("PR открытых" in str(pr["notes"]) and 1) or 0
            priv_holes += len(pr["holes"])
        else:
            p = sweep_repo(r["full_name"], False, hrs)
            (active if p["active_wave"] else pub).append(p)
        if time.time() > DEADLINE:
            break
    hole_repos = [p for p in pub if p["holes"]]
    obs_repos = [p for p in pub if not p["holes"] and p["notes"]]
    clean = [p for p in pub if not p["holes"] and not p["notes"]]
    verdict = "ДОМ ЗЕЛЁНЫЙ" if not hole_repos and priv_holes == 0 else \
              f"МЕСТА К ВЫЛИЗЫВАНИЮ: публичных {len(hole_repos)}"
    L = [f"# 🛡 ДОЗИОР АККАУНТА · {now.strftime('%Y-%m-%d %H:%M UTC')}",
         f"**Вердикт: {verdict}** · прогон {RUN_ID}",
         f"- Публичный флот: {len(pub)} чистых-по-дырам {len(pub)-len(hole_repos)} · с дырами {len(hole_repos)} · наблюдения {len(obs_repos)}",
         f"- В чужой живой волне (пуш<{ACTIVE_HOURS}ч, вне вердикта по закону §3): {len(active)}",
         f"- Приватный срез (агрегаты): дыр-флагов {priv_holes} · биллинг-заморожено прогонов {priv_billing} · репо с открытыми PR {priv_prs}",
         "- Законы: T24 пин-дозор · T25 пустые файлы · Э-2.4 «доктрина сама следит за собой» · чек-лист 01"]
    if hole_repos:
        L.append("\n## Дыры (механика канона)")
        for p in hole_repos:
            L.append(f"\n### `{p['repo']}`")
            L.extend(f"- {x}" for x in p["holes"])
    if obs_repos:
        L.append("\n## Наблюдения (не красят вердикт)")
        for p in obs_repos:
            L.append(f"- `{p['repo'].split('/')[1]}`: " + "; ".join(p["notes"]))
    if active:
        L.append("\n## В чужой живой волне (закон §3 — не трогать)")
        L.append(", ".join("`" + p["repo"].split("/")[1] + "`" for p in active))
    if not hole_repos and not obs_repos and not priv_holes:
        L.append("\nНи одного неразрешённого места. Комар носа не подточит.")
    report_md = "\n".join(L)
    if SUMMARY:
        with open(SUMMARY, "a", encoding="utf-8") as f:
            f.write(report_md + "\n")
    trace = {"generated": now.isoformat(), "run_id": RUN_ID, "verdict": verdict,
             "public_repos": len(pub), "public_hole_repos": len(hole_repos),
             "active_wave_repos": len(active),
             "private_billing_frozen": priv_billing, "private_hole_flags": priv_holes,
             "private_open_pr_repos": priv_prs,
             "public": [{"repo": p["repo"], "holes": p["holes"], "notes": p["notes"],
                         "info": p["info"]} for p in pub]}
    os.makedirs("dosezor", exist_ok=True)
    with open("dosezor/account-sentinel-latest.json", "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, indent=1)
    with open("dosezor/heartbeat.json", "w", encoding="utf-8") as f:
        json.dump({"beat": now.isoformat(), "run_id": RUN_ID, "verdict": verdict}, f, indent=1)
    ok1 = commit_file(f"{OWNER}/.github", "dosezor/account-sentinel-latest.json",
                      json.dumps(trace, ensure_ascii=False, indent=1), "main",
                      f"dosezor: след осмотра флота (run {RUN_ID})")
    ok2 = commit_file(f"{OWNER}/.github", "dosezor/heartbeat.json",
                      json.dumps({"beat": now.isoformat(), "run_id": RUN_ID, "verdict": verdict}, indent=1),
                      "main", f"dosezor: пульс (run {RUN_ID})")
    print(f"COMMIT trace={ok1} heartbeat={ok2}")
    num, st = upsert_issue(f"{OWNER}/.github", "🛡 ДОЗИОР АККАУНТА · живой осмотр флота",
                           report_md + f"\n\n---\n*автомат: account-sentinel · прогон {RUN_ID} · T24+T25+Э-2.4 · приватный срез агрегатом (мембрана приватности)*",
                           "🛡 ДОЗИОР АККАУНТА")
    print(f"ISSUE: #{num} status {st}")
    print(report_md)

if __name__ == "__main__":
    main()
