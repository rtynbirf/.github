# AGENT TRUST PASSPORT (ATP)

> Эмерджентное: maps to IETF ATEP (draft-stone-atep-02, Sep 2026). Растёт из нашего стека: ЛЕТОПИСЬ + worklog + храповик + RVL + КАНОН.

## Что это

Portable, machine-readable JSON, агрегирующий track record агента. Любой агент в доме может прочитать ATP другого агента — чтобы оценить trust перед сотрудничеством.

## Структура

```json
{
  "schema": "ATP-1.0",
  "agent_id": "z-ai",
  "sessions": [...],           // завершённые мандаты с evidence_ref
  "mistakes_recorded": [...],  // косяки из ЛЕТОПИСЬ (класс Е)
  "rvl_status": "PASS",        // Recursive Verification Loop result
  "canon_compliance": {...},   // КАНОН: structure + content layers
  "trust_score": {...},        // sessions, mistakes, repeats, RVL, full_pass
  "chain_of_attestations": {...}, // worklog hash chain + Trace + lock + RVL
  "boundaries": [...]          // что PASS не доказывает
}
```

## Связь с мировыми трендами 2026

| Тренд | Что делает | Наш ATP |
|---|---|---|
| IETF ATEP (draft-stone-atep-02) | Standard for agent verifiable track record | ATP-1.0 format, реализует ATEP concept |
| ERC-8004 (Ethereum, Feb 2026) | Trustless agents with reputation registry | ATP as portable reputation (no blockchain needed) |
| Recomputable Trust Protocol (arxiv Jun 2026) | Evidence machinery, not authority | ATP aggregates evidence, не declares trust |
| Chain of Attestations | Trust prior verified claim | ATP links worklog hash chain + Trace + lock + RVL |
| Self-healing CI (Semaphore May 2026) | CI failure → AI fix → PR | ATP records CI fix as session (hologram A-123) |

## Почему эмерджентное

ATP не копирует ATEP. ATEP — стандарт для cross-marketplace agent identity. ATP — реализация для нашего дома: агрегирует ЛЕТОПИСЬ + worklog + храповик + RVL + КАНОН в portable JSON. Растёт из нашего стека, не навязан извне.

**Сингулярное = универсальное:** ATP вырос из нашего конкретного сочетания инструментов, но применим к любому multi-agent system с worklog + mistake registry + verification loop.

## Использование

```bash
# Прочитать ATP агента перед сотрудничеством:
cat .github/docs/AGENT-TRUST-PASSPORT-Z-AI.json | python -m json.tool

# Проверить RVL status:
python -c "import json; d=json.load(open('.github/docs/AGENT-TRUST-PASSPORT-Z-AI.json')); print(d['rvl_status'])"

# Проверить trust score:
python -c "import json; d=json.load(open('.github/docs/AGENT-TRUST-PASSPORT-Z-AI.json')); print(d['trust_score'])"
```

## Границы

- ATP — self-reported. Агент сам заполняет свой passport. Вывод 5: Verifier written by verified. Для полного trust — META-AUDIT-CHECKLIST (внешний AI проверяет passport).
- ATP не доказывает, что sessions реально произошли. evidence_ref указывает на файлы — но файлы могут быть подделаны. Lock file + SHA-256 + RVL — частичная защита.
- ATP обновляется агентом после каждой сессии. Нет автоматического gate, проверяющего, что ATP обновлён. (TODO: Step 0 gate extension — проверять ATP перед операцией.)
