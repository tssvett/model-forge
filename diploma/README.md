# Diploma — ВКР Жиляева М.И.

Выпускная квалификационная работа бакалавра по теме *"Разработка микросервисной платформы для автоматической генерации 3D-моделей по 2D-изображениям с использованием методов компьютерного зрения"*.

**Студент:** Жиляев М.И., группа ГР6401, направление 01.03.02
**Научный руководитель:** Белоусов А.А., к.ф.-м.н., доцент
**Университет:** Самарский национальный исследовательский университет имени академика С.П. Королёва
**Дедлайны:** предзащита — 16.05.2026, защита — конец мая 2026

Эта папка — текстовая часть ВКР. Программная реализация платформы — в корне репозитория [model-forge](../).

## Структура

```
diploma/
├── CLAUDE.md                  Инструкции для AI-агента (auto-loaded)
├── docs/
│   ├── style-guide.md         Правила оформления (СТО СГАУ + ГОСТ 7.1)
│   ├── sources.md             Список использованных источников
│   ├── glossary.md            Согласованная терминология
│   └── narrative.md           Сюжетная нить работы
├── text/                      Главы работы в markdown
│   ├── 00-titlepage.md        Метаданные титула и реферата
│   ├── 01-intro.md            Введение
│   ├── 02-review.md           Глава 1 — Аналитический обзор
│   ├── 03-requirements.md     Глава 2 — Анализ требований
│   ├── 04-architecture.md     Глава 3 — Проектирование архитектуры
│   ├── 05-implementation.md   Глава 4 — Программная реализация
│   ├── 06-ml-finetuning.md    Глава 5 — Дообучение TripoSR
│   ├── 07-experiments.md      Глава 6 — Эксперименты
│   ├── 08-conclusion.md       Заключение
│   └── 09-references.md       Список литературы (генерируется)
├── assets/
│   ├── diagrams/              Архитектурные диаграммы (PNG, SVG)
│   └── plots/                 Графики (matplotlib скрипты + PNG)
├── scripts/
│   └── wake-up-prompt.txt     Prompt для scheduled-запуска агента
├── source-materials/          Исходные материалы (read-only)
│   ├── prior-nir/             НИР предыдущих семестров (база для главы 1)
│   ├── formatting-rules/      ГОСТы и СТО СГАУ
│   └── application/           Заявление на тему ВКР
└── README.md                  Этот файл
```

## Workflow

Диплом пишется в режиме автоматизированной автономной работы:

1. Каждый вечер в 22:00 (Windows Task Scheduler) запускается `claude` CLI с `wake-up-prompt.txt`.
2. Агент читает `CLAUDE.md`, берёт следующую готовую задачу из beads (`bd ready --label vkr`).
3. Пишет одну секцию, делает атомарный коммит в ветку `master`, выходит.
4. Утром пользователь делает ревью (`git log diploma/main`), правит при необходимости или откатывает.

## Связь с основным репозиторием

Главы 3 и 4 (архитектура и реализация) ссылаются на реальный код в:
- `../frontend/` — React SPA
- `../kotlin-service/` — Spring Boot REST API
- `../ml-service/` — Python ML Worker (TripoSR)
- `../deploy/` — docker-compose и Kubernetes манифесты

Эксперименты в главе 6 проводятся на работающей системе из этого же репозитория.

## Сборка финального документа

Этап 3 (день 17-20): сборка markdown в .docx через Pandoc с шаблоном по СТО СГАУ. Скрипт сборки — TBD (`scripts/make-pdf.sh`).

## Полезные команды

```bash
# Проверить готовность пайплайна (запускать перед автономным запуском):
bash diploma/scripts/check-scaffold.sh

# Что агент возьмёт следующим:
bd ready --label vkr --json | python -c "import json,sys; d=sorted(json.loads(sys.stdin.read()), key=lambda x:(x['priority'],x['created_at'])); print(f'{d[0][\"id\"]}: {d[0][\"title\"]}' if d else 'nothing ready')"

# Дерево задач диплома (визуализация):
bd dep tree mf-ws9

# Зарегистрировать ежевечернюю задачу в Task Scheduler (PowerShell):
powershell -ExecutionPolicy Bypass -File diploma/scripts/register-task-scheduler.ps1

# Прогон задачи прямо сейчас для проверки:
powershell -Command "Start-ScheduledTask -TaskName 'Diploma Auto-Write'"

# Что было закоммичено за сегодня в diploma/:
git log --oneline diploma/main -- diploma/
```

## Лицензия

Содержимое папки `source-materials/` — авторские материалы университета и пользователя, не для распространения. Текстовое содержимое работы — © Жиляев М.И., 2026.
