# WORK_REPORT · Волна ×10 «Доделывай недоделанное»

**Дата:** 2026-11-10 · **Аккаунт:** rtynbirf · **Мастер-индекс:** github-runbook#10 (закон §5: закрытие — только по живому зелёному прогону).

## Сделано этой волной в этом репо
- Этап ② подтверждён: `TODO.md` и `KNOWN_ISSUES.md` в корне (проверено живым API).
- Гигиена агента внесена в `AGENTS.md` (канон repo-doctrine/21-гигиена-уведомлений-и-красного-CI-2026-11-09.md).

## Состояние (живой API, 2026-11-10)
- Ветка: `main` · HEAD до волны: `4e5381a5`
- CI (последние прогоны): 25 всего; последние 6 — все success: account-facade (42613398439 schedule, 42611841800 push), ci (42611841723, 42611200002, 42611193148), account-facade 42611200170. Красного нет.
- Открытые issues: 0 ()

## Честные хвосты
- Не обнаружено; учёт ведётся в github-runbook#10.

## Дальше
- Очередь работы — в `TODO.md` этого репо и §2 реестра github-runbook#10; законы входа — в AGENTS.md.


---

# WORK_REPORT · Волна W7 «Догнать активный флот + практики 2026» (hardening, Сессия 4)

**Дата:** 2026-11-15 · **Аккаунт:** rtynbirf · **Исполнитель:** полимат-мультиагент (hardening-пакет 4, волна W7).
**Мастер-индекс:** github-runbook#10 (репо архивирован — запись туда невозможна; журнал волны: work/hardening3/W7_apply.log).

## Ландшафт (живой аудит 2026-11-15)
66 репо = **38 архив** (весь флот до 2026-11-10, включая commons/polymath-os/uace-polymat/github-runbook/polimat-hub) + 1 форк (markitdown) + **27 активных**. Волна работала только по 27 активным не-форк не-архивным.

## Сделано (apply → verify живым GET, каждая задача)
- **T-7002 PVR:** включён +0 () → GET 200 enabled=true.
- **T-7003 vulnerability alerts:** +3 (door-zero, free-man, hologram) → GET 204.
- **T-7004 Dependabot security updates:** PUT 204 ×27 → GET 200 {enabled:true}. ⚠️ Факт: GET automated-security-fixes в 2026 возвращает 200 с JSON, а не 204 — старый verify считал это «НЕТ».
- **T-7005 secret scanning + push protection:** PATCH 200 ×27 → verify GET meta enabled ×27. Факт: поля security_and_analysis в GET /repos не отдаются, пока не сделан первый PATCH.
- **T-7006 CITATION.cff:** +15 PUT 201 (из метаданных API, без выдуманных описаний).
- **T-7007/7008/7009 SECURITY.md + CODEOWNERS + dependabot.yml:** T-7007, T-7008, T-7009, T-7007, T-7008, T-7009, T-7007, T-7008, T-7009, T-7007, T-7008, T-7009, T-7007, T-7008, T-7009, T-7007, T-7008, T-7009, T-7007, T-7008, T-7009 (экосистемы: pip/npm/github-actions по файлам корня).
- **T-7010 CodeQL default setup:** +14 PATCH 202 → state=configured (итого 27/27).
- **T-7011 OpenSSF Scorecard:** +15 PUT 201 (итого 27/27; SHA scorecard-action v2.5.0 / checkout v7.0.1 / codeql-action v4.38.3 верифицированы живым GET).
- **T-7012 immutable releases:** guard чисто → PUT 204 ×21 (итого 27/27).
- **T-7013 защита main:** +14 PUT 200 (запрет force-push/удаления; итого 27/27).
- **Пилоты 2026:** `.github/workflows/zizmor.yml` (zizmor-action v0.8.1, SHA верифицирован) в .github; `security-insights.yml` (OpenSSF, схема 2.2.0 из живого example-minimum ossf) ×3: .github, combain-v2, singulyar.

## Состояние (финальный verify живым GET)
PVR 27/27 · alerts 27/27 · security-updates 27/27 · secret scanning 27/27 · push protection 27/27 · CITATION 27/27 · SECURITY.md 27/27 · dependabot.yml 27/27 · CODEOWNERS 27/27 (19 × .github/, 8 × корень — проверено живым GET) · CodeQL 27/27 · Scorecard 27/27 (25 × scorecard-analysis.yml, 2 × scorecard.yml: combain-v2, singulyar) · immutable 27/27 · защита main 27/27 · zizmor-пилот 1/1 · security-insights 3/3.

## CI волны (закон о красном CI)
- Точный проход по сегодняшним прогонам (27 репо): джобы волны W7 — Scorecard analysis, CodeQL, zizmor — **красных нет** (зелёные/завершены; 1 прогон ещё выполнялся в .github на момент проверки).
- Красные сегодня, но НЕ джобы волны: dependabot `github_actions in /. - Update` failure ×3 (edinyy-svod, hologram, polymath-core — dependabot.yml существовал до волны; связь с новыми SHA-pinned workflow — разобрать в W8); `pages build and deployment` failure ×4 (github-doctrine, event=dynamic; логи недоступны токену сессии — разбор W8); «Оракулы дома (sovereign check)» failure ×4 на ветке rumu (singulyar — ветка дома, не main).
- Cancelled ~34 — superseded pages-деплои после коммитов волны; skipped — плановые «Доктор гейтов» дома. Красными не считаются.

## Честные хвосты
1. **Дубли health-файлов:** протокол 4.2 (AGENTS.md edinyy-svod, 2026-11-11) требует наследования от хаба .github; волна W7 выравнивала 7 репо по стандарту Сессий 1-3 (per-repo). Миграция на наследование — решение Хозяина (W8): удалить per-repo SECURITY.md/CODEOWNERS или оставить.
2. **checkout тегами (v4/v7 без SHA)** найден в 13 репо — задача W8: пиннинг SHA.
3. **Мастер-индекс github-runbook#10** недоступен для записи (репо архив); факты волны зафиксированы в W7_apply.log + этот файл.
4. **Приватных репо у владельца теперь 0** (на 2026-11-10 было 15) — дизайн T-4076 (gitleaks для приватных) потерял объект; W6 закрыт как «неактуально».

## Дальше (W8 — по решению Хозяина)
zizmor-батч на остальные активные репо; security-insights.yml на остальные 24; checkout → SHA-pinning ×13; OSV-Scanner v2 пилот; перенос летописи A-… из архивного runbook в живой репо; (опционально) trusted publishing при публикации на PyPI/npm.
