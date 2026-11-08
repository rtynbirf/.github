#!/usr/bin/env python3
# generate-codeowners.py — П36: код-владелец по умолчанию на весь аккаунт.
#
# Канон генерируется здесь; файл .github/CODEOWNERS этого мета-репо —
# результат автогена (правило как у llms.txt: автоген не правят руками).
# --check  — committed файл == канон, иначе exit 1 (CI: account-facade.yml);
# --print  — показать канон;
# --audit  — живой срез: у каких репо аккаунта нет своего CODEOWNERS
#            (они наследуют дефолт отсюда; для user-аккаунта наследование —
#            доктрина + автоген-размножение, нативно это работает в orgs).
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

OWNER = "rtynbirf"
API = "https://api.github.com"
REPO = ".github"
CANON_PATH = ".github/CODEOWNERS"

CANON = """\
# Код-владелец по умолчанию — весь аккаунт rtynbirf (П36, волна ×4, 2026-11-11)
# Автоген: python3 tools/generate-codeowners.py --print > .github/CODEOWNERS
#          CI сверяет канон с файлом (account-facade.yml) — руками не править.
# Учёт: каждое новое репо без собственного CODEOWNERS наследует мембрану отсюда
# (docs/CODE-OWNER-DEFAULT.md; закрепление в repo-doctrine/04 — отдельная волна).
* @rtynbirf
"""


def _get(url: str):
    headers = {"User-Agent": "rtynbirf-codeowners-gen", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def list_repos() -> list[str]:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    base = (f"{API}/user/repos?type=owner&per_page=100" if token
            else f"{API}/users/{OWNER}/repos?per_page=100")
    names, page = [], 1
    while True:
        batch = _get(f"{base}&page={page}")
        names.extend(x["name"] for x in batch
                     if x.get("owner", {}).get("login") == OWNER or x.get("owner") is None)
        if len(batch) < 100:
            break
        page += 1
    return sorted(names)


CODEOWNERS_LOCATIONS = ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS")  # порядок GitHub


def has_codeowners(repo: str) -> bool:
    for loc in CODEOWNERS_LOCATIONS:
        try:
            _get(f"{API}/repos/{OWNER}/{repo}/contents/{loc}")
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
    return False


def audit() -> int:
    repos = list_repos()
    inherit, own = [], []
    for name in repos:
        (own if (name == REPO or has_codeowners(name)) else inherit).append(name)
    print(f"репозиторий аккаунта: {len(repos)}; со своим CODEOWNERS: {len(own)}; "
          f"наследуют дефолт: {len(inherit)}")
    if inherit:
        print("наследуют (дефолт отсюда):")
        for n in inherit:
            print(f"  - {n}")
    print(f"канон держит: {REPO}/CODEOWNERS (`* @{OWNER}`) — фасад владельца для всего аккаунта")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="П36: генератор дефолтного CODEOWNERS аккаунта")
    ap.add_argument("--check", metavar="FILE", help="сверить файл с каноном (CI-гейт)")
    ap.add_argument("--print", action="store_true", help="печатать канон")
    ap.add_argument("--audit", action="store_true", help="срез наследования по аккаунту")
    args = ap.parse_args()

    if args.print:
        sys.stdout.write(CANON)
        return 0
    if args.check:
        actual = open(args.check, encoding="utf-8").read()
        if actual != CANON:
            print(f"CODEOWNERS НЕ КАНОН: {args.check} отличается от автогена "
                  "(правь генератор, не файл)")
            return 1
        print(f"CODEOWNERS — канон ({args.check}): * @{OWNER}")
        return 0
    if args.audit:
        try:
            return audit()
        except urllib.error.HTTPError as e:
            print(f"API НЕДОСТУПЕН (HTTP {e.code}) — аудит сорван честно (fail-closed)")
            return 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
