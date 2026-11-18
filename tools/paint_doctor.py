#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 🩺 ДОКТОР ПОЛОТЕН · гейт личности полотна (T26: текст-вместо-байтов, волна РЕВО 2026-11-18)
# КЛАСС КОСЯКА (вскрыт байтами 2026-11-18, 42 полотна на 42 телах): живописец-агент
# кладёт в contents API СТРОКУ base64 вместо БАЙТОВ (у баннеров — дважды закодированную).
# raw отдаёт text/plain + nosniff, браузер обязан отказаться рисовать текст — картинка
# битая у всех посетителей при живом URL. Прошла сквозь всех стражей: ДЕЖУРНЫЙ ОБХОД
# проверял баннер только размером (>=20000 байт), а больное полотно — 77-190 КБ текста.
# КАНОН: MITRE D3-FMBV «File Magic Byte Verification» (личность файла = магия байтов) ·
# СТАНДАРТ-ДОКТОРА-ПОЛОТЕН.md (одна машина — две двери) · У-2/П3 (доказательства вместо
# заявлений: артефакт полотна = его байты) · П-36 (машинный фасад не врёт).
# РЕЖИМЫ:
#   --check        гейт: каждое полотно cwd должно быть байтами своего формата; больное —
#                  список в stdout, честный exit 1 (ничего не лечит — красный не подмазывается)
#   --local-heal   лекарь cwd: декодировать больные в настоящие байты на диске (коммит — за машиной)
#   --heal         самолекарь флота: обходит все живые репо владельца через API,
#                  декодирует и записывает полотна коммитом; архив и отказы — честный пропуск
# ТИШИНА: issue/комментарии не создаёт; доклад — stdout + GITHUB_STEP_SUMMARY.
# Токен флота: env SENTINEL_TOKEN (канон дозора). stdlib-only, биллинг-иммунитет.
import base64, os, re, sys, time, json, urllib.request, urllib.error

TOKEN = os.environ.get("SENTINEL_TOKEN", "").strip()
OWNER = "rtynbirf"
BASE = "https://api.github.com"
SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY")
DEADLINE = time.time() + 8 * 60            # канон дозора: 8 минут
MAGIC = {".png": (b"\x89PNG",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",),
         ".gif": (b"GIF8",), ".svg": (b"<svg", b"<?xml"), ".webp": (b"RIFF",)}
IMG_EXT = set(MAGIC)
PRIORITY = ("banner", "revo-page.svg", "revo-account.svg", "repo-muse.svg",
            "forge-divider.svg", "snake", "avatar", "social-preview", "header", "muse")


def real_kind(b):
    for ext, sigs in MAGIC.items():
        for s in sigs:
            if b.startswith(s):
                return ext
    return None


def looks_b64(b):
    if len(b) < 200:
        return False
    try:
        t = re.sub(rb"\s+", rb"", b).decode("ascii")
    except UnicodeDecodeError:
        return False
    return re.fullmatch(r"[A-Za-z0-9+/=]+", t) is not None


def try_decode(b):
    cur = b
    for depth in (1, 2, 3):
        try:
            cur = base64.b64decode(re.sub(rb"\s+", rb"", cur))
        except Exception:
            return None, 0
        if real_kind(cur):
            return cur, depth
        if not looks_b64(cur):
            return None, 0
    return None, 0


def sick_of(name, b):
    """Больное полотно: контент не байты своего формата. Возвращает ('T26', depth) или None."""
    ext = os.path.splitext(name)[1].lower()
    if ext not in IMG_EXT:
        return None
    if real_kind(b):
        return None
    if looks_b64(b):
        fixed, depth = try_decode(b)
        return ("T26", depth) if fixed else ("T26-безрецепт", 0)
    return ("T26-чужое-тело", 0)     # текст не base64 — полотна нет вовсе


def walk_images(root="."):
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != ".git"]
        for f in fn:
            if os.path.splitext(f)[1].lower() in IMG_EXT:
                out.append(os.path.join(dp, f))
    return sorted(out)


def mode_check():
    sick = []
    for p in walk_images():
        b = open(p, "rb").read()
        s = sick_of(os.path.basename(p), b)
        if s:
            sick.append((p, *s))
    for p, cls, depth in sick:
        print(f"  — {p}: {cls} (base64×{depth}) — текст вместо байтов")
    if sick:
        print(f"ДОКТОР ПОЛОТЕН: {len(sick)} больное(ых) полотно(а) — честный красный")
        return 1
    print("ДОКТОР ПОЛОТЕН: все полотна — настоящие байты. Тишина = айс.")
    return 0


def mode_local_heal():
    fixed = []
    for p in walk_images():
        b = open(p, "rb").read()
        if real_kind(b):
            continue
        img, depth = try_decode(b) if looks_b64(b) else (None, 0)
        if img:
            open(p, "wb").write(img)
            fixed.append(f"{p} (base64×{depth} → {len(img)} байт)")
            print("  — вылечено:", fixed[-1])
    print(f"ДОКТОР ПОЛОТЕН (локальная залечка): вылечено {len(fixed)}")
    return 0


def api(path, method="GET", data=None):
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
        try:
            return e.code, json.loads(e.read() or b"null")
        except Exception:
            return e.code, None
    except Exception as e:
        return -1, {"message": str(e)[:80]}


def heal_fleet():
    if not TOKEN:
        print("ДОКТОР ПОЛОТЕН (флот): SENTINEL_TOKEN пуст — самолекарь честно не выехал")
        return 0
    st, repos = api("/user/repos?per_page=100&sort=pushed&affiliation=owner")
    if st != 200:
        print(f"ДОКТОР ПОЛОТЕН (флот): API {st} — флот не прочитан, честный выход 0")
        return 0
    lines = ["# 🩺 Доктор полотен · самолекарь флота"]
    cured = skipped = total_sick = 0
    for r in repos:
        if time.time() > DEADLINE:
            lines.append(f"- ⏸ дедлайн дозора — осмотр прерван на `{r['name']}`")
            break
        if r["archived"]:
            continue
        full = r["full_name"]
        db = r["default_branch"]
        st, tree = api(f"/repos/{full}/git/trees/{db}?recursive=1")
        entries = (tree or {}).get("tree") or []
        cands = [t for t in entries if t.get("type") == "blob"
                 and os.path.splitext(t["path"])[1].lower() in IMG_EXT
                 and (t.get("size") or 0) < 500_000]
        cands.sort(key=lambda t: (0 if any(k in t["path"].lower() for k in PRIORITY) else 1, t["path"]))
        for t in cands[:30]:
            st, blob = api(f"/repos/{full}/git/blobs/{t['sha']}")
            if st != 200:
                continue
            b = base64.b64decode((blob or {}).get("content", "") or "")
            s = sick_of(t["path"], b)
            if not s:
                continue
            total_sick += 1
            if s[0] != "T26":
                lines.append(f"- `{full}/{t['path']}`: {s[0]} — без рецепта, НЕ тронуто")
                continue
            img, depth = try_decode(b)
            st, old = api(f"/repos/{full}/contents/{t['path']}?ref={db}")
            sha = (old or {}).get("sha") if isinstance(old, dict) else None
            data = {"message": f"доктор полотен: base64-текст → настоящие байты (T26, base64×{depth})",
                    "content": base64.b64encode(img).decode()}
            if sha:
                data["sha"] = sha
            st2, _ = api(f"/repos/{full}/contents/{t['path']}", "PUT", data)
            if st2 in (200, 201):
                cured += 1
                lines.append(f"- 🩺 `{full}/{t['path']}`: вылечено (base64×{depth})")
            else:
                skipped += 1
                lines.append(f"- ⚠ `{full}/{t['path']}`: запись отклонена HTTP {st2} — честный пропуск")
    lines.insert(1, f"**Больных найдено: {total_sick} · вылечено: {cured} · честных пропусков: {skipped}**")
    if total_sick == 0:
        lines.append("Ни одного больного полотна. Тишина = айс.")
    report = "\n".join(lines)
    print(report)
    if SUMMARY:
        with open(SUMMARY, "a", encoding="utf-8") as f:
            f.write(report + "\n")
    return 0


if __name__ == "__main__":
    mode = "--check"
    if len(sys.argv) > 1 and sys.argv[1] in ("--check", "--local-heal", "--heal"):
        mode = sys.argv[1]
    sys.exit({"--check": mode_check, "--local-heal": mode_local_heal,
              "--heal": heal_fleet}[mode]())
