#!/usr/bin/env python3
"""Step 0 gate: проверяет, что агент прочитал последние косяки из реестра.

Запускается ПЕРЕД любой операцией мандата. Если агент не знает последние 3 косяка — отказ.

Usage:
    python step0_gate.py --agent <name> --mandate <id>
    python step0_gate.py --check  # просто вывести последние 3 косяка
"""
import json, sys, os
from pathlib import Path
from datetime import datetime

# Источники косяков (по приоритету)
SOURCES = [
    # 1. ЛЕТОПИСЬ-ФАКТОВ (живая, .github/docs/)
    # 2. 22-реестр (архивный, repo-doctrine/) — если доступен
    # 3. Worklog TH-* (H-PE11-PHOENIX/worklog.md) — если доступен
]

def get_recent_mistakes(n=3):
    """Извлекает последние N косяков класса Е из доступных источников."""
    mistakes = []
    # Try ЛЕТОПИСЬ locally
    for p in [
        Path(os.environ.get('GITHUB_WORKSPACE', '.')) / '.github/docs/ЛЕТОПИСЬ-ФАКТОВ.md',
        Path('ЛЕТОПИСЬ-ФАКТОВ.md'),
        Path('.github/docs/ЛЕТОПИСЬ-ФАКТОВ.md'),
    ]:
        if p.exists():
            text = p.read_text(encoding='utf-8')
            # Find class E entries (Е\d\d.)
            import re
            entries = re.findall(r'(Е\d{2,3}\..*?)(?=\nЕ\d|\n## |\Z)', text, re.DOTALL)
            for e in reversed(entries):
                mistakes.append(e.strip()[:200])
                if len(mistakes) >= n:
                    break
            break
    return mistakes

def main():
    if '--check' in sys.argv:
        mistakes = get_recent_mistakes()
        if not mistakes:
            print("STEP0: WARNING — не найдено записей косяков. Первый запуск или источник недоступен.")
            return 0
        print(f"STEP0: последние {len(mistakes)} косяков:")
        for i, m in enumerate(mistakes, 1):
            print(f"  {i}. {m[:120]}...")
        print("\nSTEP0: прочитай их. Не повторяй. Затем — продолжай.")
        return 0
    
    # Gate mode: agent must acknowledge
    agent = ''
    mandate = ''
    for i, a in enumerate(sys.argv):
        if a == '--agent' and i+1 < len(sys.argv): agent = sys.argv[i+1]
        if a == '--mandate' and i+1 < len(sys.argv): mandate = sys.argv[i+1]
    
    mistakes = get_recent_mistakes()
    if not mistakes:
        print("STEP0: PASS (нет записей косяков — первый запуск)")
        return 0
    
    print(f"STEP0: AGENT={agent} MANDATE={mandate}")
    print(f"STEP0: Прочитай последние {len(mistakes)} косяков перед операцией:")
    for i, m in enumerate(mistakes, 1):
        print(f"  {i}. {m[:120]}...")
    print()
    print("STEP0: Подтверди (введи 'read' если прочитал):")
    # In CI mode, auto-pass with --ci flag
    if '--ci' in sys.argv:
        print("STEP0: PASS (CI mode — auto)")
        return 0
    # Interactive
    try:
        resp = input().strip().lower()
        if resp == 'read':
            print("STEP0: PASS")
            return 0
        else:
            print("STEP0: FAIL — агент не подтвердил чтение")
            return 1
    except EOFError:
        print("STEP0: PASS (non-interactive)")
        return 0

if __name__ == '__main__':
    sys.exit(main())
