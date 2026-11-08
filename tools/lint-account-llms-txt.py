#!/usr/bin/env python3
# lint-account-llms-txt.py — П36: линт машинного фасада аккаунта.
#
# «Машинный фасад не врёт»: llms-account.txt сверяется с живым API.
#   strict (есть GITHUB_TOKEN): полное равенство имён и счёта с
#                               /user/repos?type=owner — публичные и приватные;
#   public  (токена нет):       все публичные репо из /users/rtynbirf/repos
#                               присутствуют и без протухших; приватный
#                               раздел проверяется только на самосогласованность
#                               (имена недоступны анонимно — честно пропускаем);
#   offline (--offline):        самосогласованность файла (счёт == длине списков).
# Расхождение = exit 1 = красный прогон (account-facade.yml, еженедельно).
#
# Использование:
#   python3 tools/lint-account-llms-txt.py --file llms-account.txt [--offline]
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

OWNER = "rtynbirf"
API = "https://api.github.com"

H_PUB = "## Репозитории публичные"
H_PRV = "## Репозитории приватные"
H_CNT = "## Счёт"


def parse_facade(text: str) -> dict:
    """Разбор фасада: списки имён + счёт. Строгий к структуре."""
    m_pub_h = re.search(r"^## Репозитории публичные \((\d+)\)\s*$", text, re.M)
    m_prv_h = re.search(r"^## Репозитории приватные \((\d+)\)\s*$", text, re.M)
    if not m_pub_h or not m_prv_h or "## Счёт" not in text:
        raise ValueError("фасад без обязательных разделов со счётом «(N)»")

    pub_block = text[m_pub_h.end(): m_prv_h.start()]
    prv_block = text[m_prv_h.end(): text.index("## Счёт")]
    cnt_block = text[text.index("## Счёт"):]

    pub_names = re.findall(r"^- \[([^]]+)\]\(", pub_block, re.M)

    prv_names = []
    for line in prv_block.splitlines():
        line = line.strip()
        if not line or line.startswith("<!--"):
            continue
        m = re.match(r"^- (\S+) \(private\)$", line)
        if not m:
            raise ValueError(f"приватный раздел: строка не по формату: {line!r}")
        prv_names.append(m.group(1))

    counts = dict(re.findall(r"^- (public|private|total): (\d+)$", cnt_block, re.M))
    facade = {
        "pub_names": pub_names,
        "prv_names": prv_names,
        "pub_declared": int(m_pub_h.group(1)),
        "prv_declared": int(m_prv_h.group(1)),
        "counts": {k: int(v) for k, v in counts.items()},
    }
    # самосогласованность: счёт в заголовках и разделе «Счёт» == длинам списков
    if facade["pub_declared"] != len(pub_names):
        raise ValueError(f"публичные: заголовок ({facade['pub_declared']}) != списку ({len(pub_names)})")
    if facade["prv_declared"] != len(prv_names):
        raise ValueError(f"приватные: заголовок ({facade['prv_declared']}) != списку ({len(prv_names)})")
    for k, lst in (("public", pub_names), ("private", prv_names)):
        if facade["counts"].get(k) != len(lst):
            raise ValueError(f"счёт {k}: {facade['counts'].get(k)} != {len(lst)}")
    if facade["counts"].get("total") != len(pub_names) + len(prv_names):
        raise ValueError("счёт total не сходится")
    return facade


def fetch_live() -> tuple[set, set, str]:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    headers = {"User-Agent": "rtynbirf-facade-lint", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        base = f"{API}/user/repos?type=owner&per_page=100"
        mode = "strict"
    else:
        base = f"{API}/users/{OWNER}/repos?per_page=100"
        mode = "public"
    pub, prv, page = set(), set(), 1
    while True:
        req = urllib.request.Request(f"{base}&page={page}", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            batch = json.loads(r.read().decode("utf-8"))
        for x in batch:
            if x.get("owner", {}).get("login") == OWNER or (token and x.get("permissions", {}).get("admin")):
                (pub if not x.get("private") else prv).add(x["name"])
        if len(batch) < 100:
            break
        page += 1
    return pub, prv, mode


def main() -> int:
    ap = argparse.ArgumentParser(description="П36: линт account llms.txt против живого API")
    ap.add_argument("--file", default="llms-account.txt")
    ap.add_argument("--offline", action="store_true", help="без сети: только самосогласованность")
    args = ap.parse_args()

    try:
        facade = parse_facade(open(args.file, encoding="utf-8").read())
    except Exception as e:
        print(f"ФАСАД ЛОМАЕТСЯ О СТРУКТУРУ: {e}")
        return 1
    print(f"структура: public={len(facade['pub_names'])}, "
          f"private={len(facade['prv_names'])}, total={facade['counts']['total']} — самосогласована")

    if args.offline:
        print("ОФФЛАЙН: самосогласованность — фасад честен сам с собой")
        return 0

    try:
        pub_live, prv_live, mode = fetch_live()
    except urllib.error.HTTPError as e:
        print(f"API НЕДОСТУПЕН (HTTP {e.code}) — фасад не может быть сверен с живым API; "
              "по правилу fail-closed это красный, а не «может быть, всё хорошо»")
        return 1
    errs = []

    miss = sorted(pub_live - set(facade["pub_names"]))
    stale = sorted(set(facade["pub_names"]) - pub_live)
    if miss:
        errs.append(f"фасад НЕ ЗНАЕТ публичных репо ({len(miss)}): {', '.join(miss)}")
    if stale:
        errs.append(f"фасад ВРЁТ о публичных репо ({len(stale)}): {', '.join(stale)}")
    if len(facade["pub_names"]) != len(pub_live):
        errs.append(f"счёт public: фасад {len(facade['pub_names'])} != API {len(pub_live)}")

    if mode == "strict":
        miss_p = sorted(prv_live - set(facade["prv_names"]))
        stale_p = sorted(set(facade["prv_names"]) - prv_live)
        if miss_p:
            errs.append(f"фасад НЕ ЗНАЕТ приватных репо ({len(miss_p)}): {', '.join(miss_p)}")
        if stale_p:
            errs.append(f"фасад ВРЁТ о приватных репо ({len(stale_p)}): {', '.join(stale_p)}")
        if len(facade["prv_names"]) != len(prv_live):
            errs.append(f"счёт private: фасад {len(facade['prv_names'])} != API {len(prv_live)}")
    else:
        print("ПРИМЕЧАНИЕ: токена нет — приватный срез недоступен анонимно; "
              "проверены публичные имена и счёт public; strict ждёт secret ACCOUNT_TOKEN")

    if errs:
        print("ФАСАД ВРЁТ:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"ФАСАД НЕ ВРЁТ: llms-account.txt == живой API ({mode}), "
          f"public {len(facade['pub_names'])}/{len(pub_live)}, "
          f"private {len(facade['prv_names'])}" + (f"/{len(prv_live)}" if mode == 'strict' else " (не проверяемо анонимно)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
