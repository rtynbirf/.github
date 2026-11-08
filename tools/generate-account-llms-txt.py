#!/usr/bin/env python3
# generate-account-llms-txt.py — П36: автоген машинного фасада аккаунта.
#
# Источник — живой GitHub API:
#   с токеном (env GITHUB_TOKEN)  -> /user/repos?type=owner  (публичные + приватные);
#   без токена                    -> /users/rtynbirf/repos   (только публичные).
# Формат — llms.txt (llmstxt.org): заголовок, membrane, разделы-списки, счёт.
# Приватные репозитории — только имена (фасад счёта, не содержимого).
# Детерминизм: сортировка по имени; дат и изменяемых полей, кроме
# description, нет — еженедельный линт (account-facade.yml) держит фасад
# живым: расхождение с API = красный прогон.
#
# Использование:
#   python3 tools/generate-account-llms-txt.py --out llms-account.txt
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

OWNER = "rtynbirf"
API = "https://api.github.com"


def fetch_repos() -> tuple[list[dict], str]:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    headers = {"User-Agent": "rtynbirf-facade-gen", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        url = f"{API}/user/repos?type=owner&per_page=100&sort=full_name"
        mode = "authed:/user/repos (public+private)"
    else:
        url = f"{API}/users/{OWNER}/repos?per_page=100&sort=full_name"
        mode = "public:/users/rtynbirf/repos (public only)"
    repos, page = [], 1
    while True:
        req = urllib.request.Request(f"{url}&page={page}", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            batch = json.loads(r.read().decode("utf-8"))
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    mine = [r for r in repos if r.get("owner", {}).get("login") == OWNER or r.get("owner") is None]
    return mine, mode


def render(repos: list[dict], mode: str) -> str:
    repos = sorted(repos, key=lambda r: r["name"].lower())
    pub = [r for r in repos if not r.get("private")]
    prv = [r for r in repos if r.get("private")]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# {OWNER} — машинный фасад аккаунта (account llms.txt)",
        "",
        f"> Автоген {now} · источник: живой GitHub API ({mode}) · владелец {OWNER}",
        "> Правило П36: фасад не врёт. Еженедельный линт сверяет с API; расхождение = красный.",
        "",
        f"## Репозитории публичные ({len(pub)})",
    ]
    for r in pub:
        desc = (r.get("description") or "").replace("\n", " ").strip()
        lines.append(f"- [{r['name']}]({r['html_url']}) — {desc}" if desc
                     else f"- [{r['name']}]({r['html_url']})")
    lines += ["", f"## Репозитории приватные ({len(prv)})", ""]
    if prv:
        lines.append("<!-- имена без описаний: фасад счёта, не содержимого -->")
        for r in prv:
            lines.append(f"- {r['name']} (private)")
    else:
        lines.append("<!-- токена не было: приватный срез недоступен, счёт см. линт -->")
    lines += [
        "",
        "## Счёт",
        f"- public: {len(pub)}",
        f"- private: {len(prv)}",
        f"- total: {len(repos)}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="П36: автоген account llms.txt из живого API")
    ap.add_argument("--out", default="-", help="файл вывода ('-' = stdout)")
    args = ap.parse_args()
    repos, mode = fetch_repos()
    text = render(repos, mode)
    if args.out == "-":
        sys.stdout.write(text)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"фасад записан: {args.out} ({len(repos)} репо)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
