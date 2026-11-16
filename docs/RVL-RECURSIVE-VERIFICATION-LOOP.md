# RECURSIVE VERIFICATION LOOP (RVL) — эмерджентное

> Эмерджентное свойство экосистемы rtynbirf. Не копия мирового тренда — рост из комбинации.

## Что это

Verification infrastructure (lex-naturae + HUMAN-LFS) files claims **ABOUT ITSELF** in its own format, then validates those claims.

```
lex-naturae → files claim "lex-naturae has 70/70 tests" → validates with lex-naturae
HUMAN-LFS   → files node "HUMAN-LFS has 36/36 tests"    → validates with HUMAN-LFS
RVL         → both pass? → system verifies itself (one recursion level)
```

## Почему эмерджентное

**World trend 2026:** LLM self-verification (NeurIPS, ICML) — модель проверяет свой reasoning.

**Наш RVL:** system self-verification — infrastructure проверяет свою integrity.

Разница: LLM проверяет **answers**; RVL проверяет **verification rules + evidence format**.
LLM self-verification prevents **model collapse**; RVL prevents **trust collapse**.

## Рост из комбинации

RVL растёт из сочетания:
- **КАНОН-ПРОВЕРКИ-CLAIMS** (двухслойная проверка: structure + content)
- **Храповик** (22-реестр + ЛЕТОПИСЬ: mistakes don't repeat)
- **Step 0 gate** (read before act)
- **Proactive fuzz** (hunt new bypass classes)
- **Meta-audit checklist** (who audits the auditor)

Ни один компонент alone не даёт RVL. Только их комбинация.

## Запуск

```bash
python .github/scripts/recursive_verify_loop.py
```

Вывод:
```
=== RECURSIVE VERIFICATION LOOP (RVL) ===
Layer 1: lex-naturae files claim about lex-naturae
  claim: lex-naturae has 70 tests, status=SUPPORTED
Layer 2: HUMAN-LFS files node about HUMAN-LFS
  node: HUMAN-LFS has 36 tests, status=PASS
Layer 3: Recursive verification result
  RVL: PASS — verification system verifies itself
```

## Что значит PASS

- lex-naturae принял собственный claim (lex-naturae test count) в своём формате
- HUMAN-LFS принял собственный node (HUMAN-LFS test count) в своём графе
- Verification infrastructure верифицирует себя на одном уровне рекурсии

## Что значит FAIL

- Один из validators не принял meta-claim о себе
- Это означает: verification system нашла свой собственный gap
- Действие: записать gap в ЛЕТОПИСЬ, починить, перегнать

## Границы

- **One level of recursion.** RVL проверяет себя один раз. Deep recursion (проверка проверки проверки...) — не реализована. Для practical purposes, один уровень достаточен: если система не может верифицировать себя один раз, deeper recursion не поможет.
- **Self-tested tests.** Тесты написаны тем же автором, что и код (вывод 5). RVL не решает это — для полного решения нужен независимый свидетель (META-AUDIT-CHECKLIST).
- **Format tautology.** lex-naturae claim about lex-naturae uses lex-naturae format — это может быть тавтологией (формат всегда принимает себя). Защита: HUMAN-LFS layer (structure check) и META-AUDIT-CHECKLIST (external AI).

## Связь с мировыми трендами

| Тренд 2026 | Что делает | Наш RVL |
|---|---|---|
| LLM self-verification (NeurIPS) | Модель проверяет reasoning | Infrastructure проверяет integrity |
| Multi-agent verification | Агенты проверяют друг друга | Система проверяет себя |
| Evidence-driven CI (arxiv) | CI produces evidence | CI infrastructure produces evidence about itself |
| Inline provenance (ICSE) | Trace agent actions | Trace verification actions recursively |
| Self-healing → self-architecture | System fixes itself | System verifies its own fixing |
