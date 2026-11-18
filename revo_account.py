#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""РЕВО-ПАСПОРТ АККАУНТА — движок самообновления профиля rtynbirf/rtynbirf.
Тянет живые факты аккаунта по публичному API, куёт revo-account.svg (68 плит мастеровских,
живые/архив, статистика), обновляет README между маркерами. Только stdlib — живёт в Actions."""
import json, os, re, urllib.request

try:
    ROSTER = json.loads(r'''[["index", 1, "ШВЕЙЦАРСКАЯ ШКОЛА"], ["singulyar", 1, "КАНДИНСКИЙ · КОМПОЗИЦИЯ"], ["edinyy-svod", 3, "КУПОЛ БРУНЕЛЛЕСКИ"], ["lean-canon", 4, "AGNES MARTIN"], ["ekonomika", 5, "МИНАРД · ПОТОК"], ["revo", 6, "БАУХАУС · АЛЬБЕРС"], ["polymath-core", 7, "ВИТРУВИЙ · ЧЕРТЁЖ"], ["cell65-host", 8, "КАЛДЕР · МОБИЛЬ"], ["ekspozicii", 9, "АР-ДЕКО"], ["github-doctrine", 10, "ПЕРВОПЕЧАТНИК"], ["rtynbirf", 11, "ФРИДРИХ · ПУТНИК"], ["rtynbirf.github.io", 12, "ХОКУСАЙ · ВОЛНА"], ["domovoy", 13, "ЭНСО · КИСТЬ"], ["combain-v2", 14, "КОММУТАТОР"], ["ruvson", 15, "ВАН ГОГ · ВИХРЬ"], ["uace", 16, "МОНДРИАН · БУГИ"], [".github", 17, "МОРИСС · РАППОРТ"], ["agryp", 18, "РАДАР-ГЛАЗ"], ["neutral-browser", 19, "МАГРИТТ · АРКАДА"], ["release-vault", 20, "ПИРАНЕЗИ · СВОДЫ"], ["H-PE11-PHOENIX", 21, "ФЕНИКС АР-НУВО"], ["POLYMATH-ATLAS-GESTALT-CANON", 22, "КАНОН ПРОПОРЦИЙ"], ["cell-rs", 23, "КЛАДКА RUST"], ["cell-swarm", 24, "ПОЛЛОК · РОЙ"], ["commons", 25, "КРУГЛЫЙ СТОЛ"], ["domovenok", 26, "ШАГАЛ · ПОЛЁТ"], ["domovoy-ritual", 27, "КЛИМТ · ЗОЛОТАЯ ФАЗА"], ["domovoy-tweaker", 28, "ВЕРСТАК"], ["github-runbook", 29, "ЧЕРТЁЖ-РУНБУК"], ["global-video-platforms-registry", 30, "КАРТА ЭФИРА"], ["karaoke-dream", 31, "СЦЕНА СОФИТОВ"], ["khozyain", 32, "ТЁРНЕР · ВИХРЬ"], ["singulyar-a0-audit", 32, "МАСТЕРСКАЯ ДОМА"], ["language-through-the-ages", 33, "ВАВИЛОН · СТРОКИ"], ["linguistic-code", 34, "СИНТАКС-ДРЕВО"], ["markitdown", 35, "ЛИНОТИП"], ["nous", 36, "МАЛЕВИЧ · БЕЛОЕ"], ["os-forge", 37, "КУЗНЯ"], ["polimat-hub", 38, "КЛЕЕ · ЛИНИЯ"], ["polimat-task174", 39, "БРУТАЛ · 174"], ["polymat-hive", 40, "УЛЕЙ"], ["polymath-atlas", 41, "ПОРТОЛАН · КАРТА"], ["polymath-atlas-v107", 42, "CELESTIAL CHART"], ["polymath-gen", 43, "ЛОЗА ГЕНАРАЦИЙ"], ["polymath-multiagent", 44, "ЛИСИЦКИЙ · КЛИН"], ["polymath-os", 45, "МАШИННАЯ МАНДАЛА"], ["polymath-stckg-core", 46, "ВАЗАРЕРИ · ТУННЕЛЬ"], ["polymath-tools-atlas", 47, "ДЮРЕР · ВИТРИНА"], ["red-thread-debt-audit", 48, "КРАСНАЯ НИТЬ"], ["rent-mechanism-q43", 49, "ДА ВИНЧИ · МЕХАНИЗМ"], ["repo-doctrine", 50, "СТЕЛА ЗАКОНА"], ["runtime-protocol", 51, "ОСЦИЛЛОГРАФ"], ["ruvson-lyrics", 52, "АРАБЕСКА СТРОК"], ["ruvson-rse2", 53, "НОТЫ-ЛЕНТЫ"], ["singulyar-llm", 54, "ПРОФИЛЬ-СОЗВЕЗДИЕ"], ["task-graph-propagator", 55, "ДРЕВО ЗАДАЧ"], ["uace-pml", 56, "ПЕРФОКАРТА"], ["uace-polymat", 57, "ТАТЛИН · БАШНЯ"], ["universal-agent", 58, "РУКА ЛЕОНАРДО"], ["voice-atlas-llm", 59, "АРФА ГОЛОСОВ"], ["web-evolution-1991-2026", 60, "РЕКА ВЕБА"], ["windows-chronicle", 61, "АРКАДА ЭПОХ"], ["yazyk-skvoz-epohi", 62, "КОЛОННА ПИСЬМЕН"], ["rumu", 63, "САРКОФАГ · УДЖАТ"], ["free-man", 64, "ПРОЁМ СВЕТА"], ["door-zero", 65, "ПУСТОЙ ПРОЁМ"], ["hologram", 66, "МЕРКЛ"], ["fond-host", 67, "НОВАЯ МАСТЕРСКАЯ"], ["lex-naturae", 69, "НОВАЯ МАСТЕРСКАЯ"], ["karta", 70, "МАСТЕРСКАЯ КАРТ"], ["kb", 71, "МАСТЕРСКАЯ ЗНАНИЙ"], ["code", 72, "МАСТЕРСКАЯ КОДА"], ["invariant-manifest", 73, "МАСТЕРСКАЯ ИНВАРИАНТОВ"]]''')  # [[имя, номер, школа], ...]
except Exception:
    ROSTER = []

MONO = "'Cascadia Mono', ui-monospace, Consolas, monospace"
SERIF = "Georgia, 'Times New Roman', serif"
REVO = "#D5281B"
NEUTRAL = dict(bg="#EDE9E0", bg2="#F4F1EA", ink="#17150F", gold="#8A6D2F", gold2="#B08D3E", dim="#6E675B")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fetch_facts():
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
    out, page = [], 1
    while True:
        req = urllib.request.Request(
            f"https://api.github.com/users/rtynbirf/repos?per_page=100&page={page}",
            headers={"Accept": "application/vnd.github+json",
                     **({"Authorization": f"Bearer {tok}"} if tok else {}),
                     "User-Agent": "revo-account"})
        with urllib.request.urlopen(req, timeout=60) as r:
            batch = json.load(r)
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    topics = {}
    for r in out:
        for t in r.get("topics") or []:
            topics[t] = topics.get(t, 0) + 1
    pushed = max((r.get("pushed_at") or "") for r in out) or ""
    return {"total": len(out), "living": sum(1 for r in out if not r.get("archived")),
            "archived": sum(1 for r in out if r.get("archived")),
            "topics": [t for t, _ in sorted(topics.items(), key=lambda kv: (-kv[1], kv[0]))[:4]],
            "last_push": pushed[:10],
            "archived_set": {r["name"] for r in out if r.get("archived")}}


def render_account(f):
    pal = NEUTRAL
    bg, bg2, ink, gold, gold2, dim = pal["bg"], pal["bg2"], pal["ink"], pal["gold"], pal["gold2"], pal["dim"]
    e = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 400" width="1280" height="400">']
    e.append(f'<defs><radialGradient id="ra1" cx="0.5" cy="0.46" r="1.05">'
             f'<stop offset="0" stop-color="{bg2}"/><stop offset="1" stop-color="{bg}"/></radialGradient></defs>')
    e.append(f'<rect width="1280" height="400" fill="{bg}"/><rect width="1280" height="400" fill="url(#ra1)" opacity="0.92"/>')
    e.append(f'<rect x="14" y="14" width="1252" height="372" fill="none" stroke="{gold}" stroke-width="1.3"/>')
    e.append(f'<rect x="22" y="22" width="1236" height="356" fill="none" stroke="{gold}" stroke-width="0.55" opacity="0.55"/>')
    for (x, y, dx, dy) in ((22, 22, 1, 1), (1258, 22, -1, 1), (22, 378, 1, -1), (1258, 378, -1, -1)):
        e.append(f'<path d="M {x} {y+dy*13} L {x} {y} L {x+dx*13} {y}" fill="none" stroke="{gold2}" stroke-width="1.4"/>')
    e.append(f'<path d="M 22 54 L 22 22 L 54 22 Z" fill="{REVO}"/>')
    e.append(f'<text x="64" y="66" font-family="{MONO}" font-size="11" fill="{gold}" letter-spacing="4">РЕВО-ПАСПОРТ АККАУНТА · КУЗНЯ ПОЛИМАТ · АВТОПИЛОТ НА КАЖДОЙ СТРАНИЦЕ</text>')
    e.append(f'<text x="64" y="150" font-family="{SERIF}" font-size="54" fill="{ink}" letter-spacing="6">RTYNBIRF</text>')
    e.append(f'<line x1="64" y1="178" x2="740" y2="178" stroke="{gold}" stroke-width="1" opacity="0.85"/>')
    e.append(f'<text x="64" y="206" font-family="{MONO}" font-size="13" fill="{dim}">Дом мастеровских: каждая страница несёт полотно, паспорт и самообновление</text>')
    for i, (lab, v) in enumerate([("РЕПО", f["total"]), ("ЖИВЫХ", f["living"]), ("МАСТЕРСКИХ", len(ROSTER) or f["total"])]):
        cx = 109 + i * 145
        e.append(f'<g transform="translate({cx},278)"><circle r="25" fill="none" stroke="{REVO}" stroke-width="1.2"/>'
                 f'<text y="4.5" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{gold2}">{v}</text>'
                 f'<text y="44" text-anchor="middle" font-family="{MONO}" font-size="9.5" fill="{dim}" letter-spacing="2">{lab}</text></g>')
    lx = f["topics"][:4]
    cx = 460
    for w in lx:
        cw = int(len(w) * 9.2 + 24)
        e.append(f'<rect x="{cx}" y="318" width="{cw}" height="22" fill="none" stroke="{gold2}" stroke-width="0.9"/>'
                 f'<text x="{cx+cw/2:.0f}" y="333" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{ink}" letter-spacing="1">{esc(w)}</text>')
        cx += cw + 10
    x0, y0, tw, th, gx, gy = 800, 88, 44, 22, 5, 6
    arch = f.get("archived_set") or set()
    for i, (name, num, school) in enumerate(sorted(ROSTER, key=lambda x: x[1])):
        col, row = i % 9, i // 9
        tx, ty = x0 + col * (tw + gx), y0 + row * (th + gy)
        alive = name not in arch
        fillc = gold2 if alive else dim
        op = 0.9 if alive else 0.28
        e.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" fill="{fillc}" opacity="{op}" rx="2"/>')
        e.append(f'<text x="{tx+tw/2:.0f}" y="{ty+14}" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{bg2}">{num}</text>')
    e.append(f'<text x="{x0}" y="{y0 + 8*(th+gy) + 18}" font-family="{MONO}" font-size="9.5" fill="{dim}" letter-spacing="2">■ ЖИВЫЕ МАСТЕРСКИЕ · □ АРХИВ · НОМЕР = № ПОЛОТНА</text>')
    e.append(f'<line x1="64" y1="348" x2="1216" y2="348" stroke="{gold}" stroke-width="0.6" opacity="0.5"/>')
    e.append(f'<text x="640" y="371" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{dim}" letter-spacing="2">'
             f'ОБНОВЛЕНО {esc(f["last_push"])} · РЕВО В ОСНОВЕ ВСЕГО · REVE=РЕВО · ЧЕЛОВЕК=АККАУНТ=PID1</text>')
    e.append("</svg>")
    return "".join(e)


def patch_readme(md, f):
    block = ("<!--ФОРЖ:АККАУНТ:НАЧАЛО-->\n"
             '<div align="center">\n'
             '  <img src="revo-account.svg" width="100%" alt="РЕВО-паспорт аккаунта: мастераские, живые/архив, автопилот на каждой странице" />\n'
             "</div>\n\n"
             "| РЕПО | ЖИВЫХ | МАСТЕРСКИХ | ОБНОВЛЕНО |\n|---:|---:|---:|---|\n"
             f'| {f["total"]} | {f["living"]} | {len(ROSTER) or f["total"]} | {f["last_push"]} |\n'
             "<!--ФОРЖ:АККАУНТ:КОНЕЦ-->")
    if "<!--ФОРЖ:АККАУНТ:НАЧАЛО-->" in md:
        return re.sub(r"<!--ФОРЖ:АККАУНТ:НАЧАЛО-->.*?<!--ФОРЖ:АККАУНТ:КОНЕЦ-->", block.replace("\\", "\\\\"), md, flags=re.S)
    if "<!--ФОРЖ:ПАСПОРТ:КОНЕЦ-->" in md:
        return md.replace("<!--ФОРЖ:ПАСПОРТ:КОНЕЦ-->", "<!--ФОРЖ:ПАСПОРТ:КОНЕЦ-->\n\n" + block, 1)
    if "<!--ФОРЖ:МУЗА:КОНЕЦ-->" in md:
        return md.replace("<!--ФОРЖ:МУЗА:КОНЕЦ-->", "<!--ФОРЖ:МУЗА:КОНЕЦ-->\n\n" + block, 1)
    i = md.find("</div>")
    if i != -1 and md.find("<div") != -1 and i - md.find("<div") < 600:
        return md[:i + 6] + "\n\n" + block + md[i + 6:]
    return block + "\n\n" + md


if __name__ == "__main__":
    f = fetch_facts()
    open("revo-account.svg", "w", encoding="utf-8").write(render_account(f))
    if os.path.exists("README.md"):
        md = open("README.md", encoding="utf-8").read()
        open("README.md", "w", encoding="utf-8").write(patch_readme(md, f))
    print(f"РЕВО-ПАСПОРТ АККАУНТА: репо {f['total']}, живых {f['living']}, обновлено {f['last_push']}")
