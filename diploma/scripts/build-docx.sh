#!/usr/bin/env bash
# Сборка ВКР в docx через Pandoc по шаблону Маршуниной.
# Запускать из корня diploma/: bash scripts/build-docx.sh [имя_файла.docx]
# Опции:
#   --check   только валидирует ссылки на изображения в text/*.md, не собирает docx.
#   -h|--help справка.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_OUTPUT="ВКРБ_ЖиляевМИ.docx"
TEMPLATE_REL="template/blank-template.docx"

CHAPTERS=(
    "text/00-titlepage.md"
    "text/00b-abbreviations.md"
    "text/01-intro.md"
    "text/02-review.md"
    "text/03-requirements.md"
    "text/04-architecture.md"
    "text/05-implementation.md"
    "text/06-ml-finetuning.md"
    "text/07-experiments.md"
    "text/08-conclusion.md"
    "text/09-references.md"
)

usage() {
    cat <<EOF
Использование: bash scripts/build-docx.sh [имя_файла.docx] [--check]

Без аргументов:    собрать ${DEFAULT_OUTPUT} в текущей директории.
[имя_файла.docx]:  переопределить имя выходного файла.
--check:           только проверить ссылки на изображения в text/*.md.
-h, --help:        показать эту справку.
EOF
}

CHECK_ONLY=0
OUTPUT="${DEFAULT_OUTPUT}"
for arg in "$@"; do
    case "${arg}" in
        --check)        CHECK_ONLY=1 ;;
        -h|--help)      usage; exit 0 ;;
        --*)            echo "Неизвестная опция: ${arg}" >&2; usage; exit 2 ;;
        *)              OUTPUT="${arg}" ;;
    esac
done

cd "${ROOT_DIR}"

missing=0
for ch in "${CHAPTERS[@]}"; do
    if [[ ! -f "${ch}" ]]; then
        echo "ОТСУТСТВУЕТ: ${ch}" >&2
        missing=1
    fi
done
if (( missing )); then
    echo "Сборка прервана: не все главы найдены." >&2
    exit 1
fi

if [[ ! -f "${TEMPLATE_REL}" ]]; then
    echo "ОТСУТСТВУЕТ шаблон: ${TEMPLATE_REL}" >&2
    exit 1
fi

# Валидация ссылок на изображения вида ![alt](path).
broken=0
checked=0
for ch in "${CHAPTERS[@]}"; do
    base_dir="$(dirname "${ch}")"
    while IFS= read -r raw; do
        # Извлечь путь между скобками; игнорировать http(s)/data: ссылки.
        path="${raw}"
        case "${path}" in
            http://*|https://*|data:*)
                continue ;;
        esac
        # Очистить возможный заголовок в кавычках.
        path="${path%% *}"
        # Разрешить путь относительно директории файла главы.
        resolved="${base_dir}/${path}"
        # Нормализовать ../ за счёт cd.
        resolved_dir="$(dirname "${resolved}")"
        resolved_name="$(basename "${resolved}")"
        if [[ -d "${resolved_dir}" ]]; then
            abs="$(cd "${resolved_dir}" && pwd)/${resolved_name}"
        else
            abs="${resolved}"
        fi
        checked=$((checked + 1))
        if [[ ! -f "${abs}" ]]; then
            echo "БИТАЯ ССЫЛКА: ${ch}: ${path}" >&2
            broken=$((broken + 1))
        fi
    done < <(grep -oE '!\[[^]]*\]\(([^)]+)\)' "${ch}" | sed -E 's/.*\(([^)]+)\).*/\1/')
done

echo "Проверено ссылок на изображения: ${checked}, повреждено: ${broken}"

if (( broken )); then
    echo "Найдены битые ссылки на изображения." >&2
    if (( CHECK_ONLY )); then
        exit 1
    fi
    echo "Сборка прервана из-за битых ссылок." >&2
    exit 1
fi

if (( CHECK_ONLY )); then
    echo "Режим --check: ссылки валидны, сборка пропущена."
    exit 0
fi

if ! command -v pandoc >/dev/null 2>&1; then
    echo "Не найден pandoc. Установите Pandoc и повторите запуск." >&2
    exit 1
fi

LUA_FILTER_REL="scripts/apply-stosgau-styles.lua"
if [[ ! -f "${LUA_FILTER_REL}" ]]; then
    echo "ОТСУТСТВУЕТ Lua-фильтр: ${LUA_FILTER_REL}" >&2
    exit 1
fi

echo "Сборка ${OUTPUT} ..."
pandoc \
    "${CHAPTERS[@]}" \
    -o "${OUTPUT}" \
    --reference-doc="${TEMPLATE_REL}" \
    --lua-filter="${LUA_FILTER_REL}" \
    --resource-path=. \
    --toc \
    --toc-depth=3 \
    --number-sections=false

echo "Готово: ${OUTPUT}"
