#!/usr/bin/env python3
"""HOUSE-KEEPER — эмерджентный автопилот дома rtynbirf.

Рост из нашего стека: Step 0 gate + Ф0 ЗАМЕР + I-3 inbox-zero + I-1 red CI + token audit.
Maps to world trend: CI gates for AI agents (2026), automated housekeeping, self-healing CI.

Usage:
    python house-keeper.py --check       # read-only audit, print report
    python house-keeper.py --fix         # fix what's auto-fixable (notifications, topics)
    python house-keeper.py --step0       # Step 0 gate: print last 3 косяки
"""
import json, os, re, sys, urllib.request, urllib.error
from datetime import date, datetime, timezone

TOKEN = os.environ.get("GH_TOKEN", "")
API = "https://api.github.com"
USER = "rtynbirf"
TODAY = date.today().isoformat()

def gh(path, method="GET", data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{API}{path}", data=body, method=method, headers={
        "Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}") if r.status != 204 else {}
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

def get_repos():
    repos = []
    page = 1
    while True:
        _, data = gh(f"/user/repos?per_page=100&page={page}&type=all&sort=pushed&direction=desc")
        if not isinstance(data, list) or not data: break
        repos.extend(data)
        page += 1
    return [r for r in repos if not r["archived"] and not r["fork"]]

def check_inbox():
    """I-3: Inbox-zero"""
    _, notifs = gh("/notifications?per_page=100")
    count = len(notifs) if isinstance(notifs, list) else 0
    return count

def fix_inbox():
    """Mark all as read"""
    code, _ = gh("/notifications?last_read_at=" + datetime.now(timezone.utc).isoformat(), "PUT", {})
    return code == 205

def check_red_ci(repos):
    """I-2: Last CI run green per repo"""
    red = []
    for r in repos[:20]:  # top 20
        _, runs = gh(f"/repos/{USER}/{r['name']}/actions/runs?per_page=1")
        if isinstance(runs, dict) and runs.get("workflow_runs"):
            c = runs["workflow_runs"][0].get("conclusion", "")
            if c == "failure":
                red.append(r["name"])
    return red

def check_fat(repos):
    """AGENTS.md: ЖИР >1MB"""
    fat = [(r["name"], r["size"]) for r in repos if r["size"] > 1024]
    return sorted(fat, key=lambda x: -x[1])

def check_topics(repos):
    """AGENTS.md: 3-7 topics"""
    low = [r["name"] for r in repos if len(r.get("topics", [])) < 3]
    return low

def check_license(repos):
    """AGENTS.md: license required"""
    nolic = [r["name"] for r in repos if not r.get("license")]
    return nolic

def step0():
    """Step 0 gate: print last 3 косяки from ЛЕТОПИСЬ"""
    enc = urllib.request.quote("docs/ЛЕТОПИСЬ-ФАКТОВ.md", safe="/")
    _, d = gh(f"/repos/{USER}/.github/contents/{enc}")
    if isinstance(d, dict) and d.get("content"):
        import base64
        text = base64.b64decode(d["content"]).decode("utf-8")
        mistakes = re.findall(r"(Е\d{2,3}\..*?)(?=\nЕ\d|\n## |\Z)", text, re.DOTALL)
        print("STEP 0: последние косяки:")
        for m in mistakes[-3:]:
            print(f"  {m.strip()[:120]}")
        print("\nПрочитай. Не повторяй.")

def main():
    args = sys.argv[1:]
    
    if "--step0" in args:
        step0()
        return 0
    
    print(f"HOUSE-KEEPER · {TODAY} · rtynbirf")
    print("=" * 60)
    
    repos = get_repos()
    print(f"Active repos: {len(repos)}")
    
    # I-3: Inbox
    inbox = check_inbox()
    status = "PASS" if inbox == 0 else f"FAIL ({inbox} unread)"
    print(f"I-3 Inbox-zero: {status}")
    if "--fix" in args and inbox > 0:
        if fix_inbox():
            print(f"  FIXED: marked {inbox} as read")
    
    # I-2: Red CI
    red = check_red_ci(repos)
    status = "PASS" if not red else f"FAIL ({', '.join(red)})"
    print(f"I-2 Red CI: {status}")
    
    # ЖИР repos
    fat = check_fat(repos)
    print(f"ЖИР repos (>1MB): {len(fat)}")
    for name, size in fat[:5]:
        print(f"  {name}: {size}KB")
    
    # Topics
    low = check_topics(repos)
    print(f"Low topics (<3): {len(low)} — {', '.join(low[:5])}")
    
    # License
    nolic = check_license(repos)
    print(f"No license: {len(nolic)} — {', '.join(nolic)}")
    
    # Summary
    issues = inbox + len(red) + len(fat) + len(low) + len(nolic)
    print(f"\nTOTAL ISSUES: {issues}")
    if issues == 0:
        print("HOUSE: CLEAN")
        return 0
    else:
        print("HOUSE: NEEDS ATTENTION")
        return 1

if __name__ == "__main__":
    sys.exit(main())
