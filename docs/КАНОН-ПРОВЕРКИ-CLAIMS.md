# КАНОН ПРОВЕРКИ CLAIMS — синтез HUMAN-LFS + lex-naturae

> Мандат Хозяина 2026-11-16: «синтезировать, интегрировать, запушить и вписать в канон правил для агентов, что они это применяли на практике, а не декларировали».

## Принцип

**Два слоя проверки — структурный и содержательный.**

| Слой | Инструмент | Что проверяет | Где живёт |
|---|---|---|---|
| **Структура** | HUMAN-LFS `validate_graph.py` | Узел в графе зависимостей; DAG; chroot-правило; lock; falsification condition; status PASS требует evidence | `singulyar-a0-audit/human-lfs/v0.4/` |
| **Содержание** | lex-naturae `lex_naturae.py` | CSV cell extraction; excerpt verbatim; SHA-256 artifact; unit ranges; date validation; deduplication | `lex-naturae` (standalone repo) |

**Ни один слой alone не достаточен.** Структура без содержания — список желаний. Содержание без структуры — разрозненные факты без графа зависимостей.

## Обязательная процедура для агентов

**Прежде чем объявить результат («готово», «VALID», «PASS», «SUPPORTED»):**

### Шаг 1: Структурный — HUMAN-LFS
1. Запиши claim как узел в `BUILD_GRAPH.json`:
   - `id`: уникальный ASCII идентификатор
   - `source`: минимум один источник с `type`, `uri`, `claim` (не только conversation)
   - `status`: UNKNOWN по умолчанию; PASS только с evidence
   - `falsification_or_revision_condition`: обязательно — при каких условиях claim признаётся ошибочным
   - `depends_on`: `{build:[], runtime:[]}` — зависимости от других узлов
   - `scaffold`: true/false — является ли временным лесом
   - `replaceable_by`: чем можно заменить
2. Прогони: `python validate_graph.py`
3. Результат: `STRUCTURE: PASS` — узел в валидном графе. `STRUCTURE: FAIL` — правь граф.

### Шаг 2: Содержательный — lex-naturae
1. Запиши evidence для claim:
   - `method: measurement` → `measurement_value` сверяется с CSV-ячейкой (`csv_row`, `csv_column`, `tolerance` ≤1%)
   - `method: log_analysis` → `excerpt` проверяется verbatim по тексту файла
   - `raw_data_ref` + `raw_data_sha256` → SHA-256 пересчитывается от файла
2. Прогони: `python lex_naturae.py claims.json`
3. Результат: `valid=true` — evidence подтверждено machine-verifiable. `valid=false` — правь evidence.

### Шаг 3: Объявление
- **STRUCTURE: PASS** + **lex-naturae valid=true** → можно объявить результат.
- Любой FAIL → результат не объявляется. `status` остаётся UNKNOWN.

## Референс-реализации

| Кто | Что | HUMAN-LFS | lex-naturae | Результат |
|---|---|---|---|---|
| Z.ai | A0 PACKAGE VALID audit | — (не в графе) | valid=true (CSV cell + log excerpt) | PASS |
| Z.ai | BRIDGE VALID audit | — | valid=true | PASS |
| Z.ai | R4 X019 minimal | — | valid=true | PASS |
| Z.ai | Ecosystem inventory | — | valid=true (SBOM, DORA, deps) | PASS |
| Коллега | HUMAN-LFS environment | PASS (node in graph, evidence) | — (evidence not in lex-naturae format) | PASS (structural only) |
| Коллега | HUMAN-LFS human_core | PASS (node in graph) | — (no evidence, status UNKNOWN) | UNKNOWN |

**Полный PASS** = STRUCTURE PASS + lex-naturae valid=true. Референса полного PASS пока нет — это цель v0.5.

## Что НЕ является PASS

- «Я запустил тесты, они прошли» → UNKNOWN, пока evidence не записан в lex-naturae формате
- «Структура валидна» → STRUCTURE PASS, но если status=UNKNOWN — claim не подтверждён
- «README говорит что всё работает» → декларация, не evidence
- «SHA-256 совпадает» → целостность файла, не истинность содержания (вывод из audit lex-naturae v0.4)

## Границы (честно)

1. **URL content verification** — ни HUMAN-LFS, ни lex-naturae не fetching URLs. Source URI проверяется на формат, не на содержание.
2. **Lock self-attestation** — если изменить и граф, и lock файл, validator passes. Внешний witness нужен.
3. **Semantic vacuity** — расширенный TRIVIAL set ловит известные фразы, но не все возможные.
4. **Excerpt cherry-picking** — цитата найдена verbatim, но контекст может быть negation (semantic gap).

## Для агентов: минимальный пакет

```
my-claim/
├── BUILD_GRAPH.json          # HUMAN-LFS: claim как узел в графе
├── evidence/
│   ├── results.csv           # CSV с реальными данными (measurement)
│   └── output.log            # лог с дословным выводом (excerpt)
├── claims.json               # lex-naturae: claim + evidence records
└── run_check.sh              # python validate_graph.py && python lex_naturae.py claims.json
```

Запусти `run_check.sh`. Если оба PASS — объявляй результат. Если любой FAIL — status=UNKNOWN.


## Что PASS не доказывает (границы machine-verifiable)

**PASS = machine-verifiable, не = истина.** Два слоя проверки ловят структурные и содержательные нарушения, но не семантические:

1. **Excerpt cherry-pick.** Цитата найдена verbatim, но вырвана из контекста negation. Tool не понимает смысл.
2. **Fake source URL.** URL в `source` и `source_ref` — правильный формат, но содержимое не fetching'ся. URL может быть фейковым.
3. **Semantic vacuity.** Расширенный TRIVIAL set ловит известные пустые фразы, но не все возможные. «checked it works» поймано; «the system performed as expected within parameters» — нет.
4. **Lock self-attestation.** Если изменить и граф, и lock файл одновременно — validator passes. Внешний witness нужен.
5. **Self-tested tests.** Тесты, написанные тем же агентом, что и код, всегда дают fails=0 (вывод 5 из 22-реестра). Нужен независимый прогон.

**PASS = «лучше, чем декларация», но не = «доказано».** Для полного доказательства нужен независимый свидетель (другой агент, другая модель, внешний аудит).
