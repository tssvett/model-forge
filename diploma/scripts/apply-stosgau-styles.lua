-- apply-stosgau-styles.lua
-- Pandoc Lua-фильтр: маппинг markdown-элементов на кастомные стили
-- шаблона Маршуниной (template/blank-template.docx, стили с префиксом '+').
--
-- Применяется через `pandoc --lua-filter=scripts/apply-stosgau-styles.lua
--                          --reference-doc=template/blank-template.docx`.
--
-- Имя стиля в attributes['custom-style'] — это display name стиля Word,
-- pandoc найдёт соответствующий styleId в reference-doc и применит его.
--
-- ВАЖНО: вся логика собрана в Pandoc(doc), а не в раздельных Header/Para
-- callback'ах, по двум причинам:
--   1) Нужен сквозной обход блоков в порядке документа, чтобы переключать
--      режим "сейчас идёт список источников" по факту встречи заголовка
--      "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ".
--   2) После замены Header → Div сторонние walker'ы перестают видеть Header
--      по типу (block.t == "Header"), поэтому делаем всё в одном проходе.
--
-- Ещё одно гнусное место: класс `%s` в Lua-паттернах Pandoc сматчивает
-- байт 0xA0 (часть UTF-8-последовательности кириллической "Р" = d0 a0),
-- что портит содержимое кириллических строк. Поэтому пробельные подмножества
-- задаются явным ASCII-классом `[ \t\n\r\f\v]`.

local pandoc = pandoc

local WS = "[ \t\n\r\f\v]"

local function trim(s)
    s = s:gsub("^" .. WS .. "+", "")
    s = s:gsub(WS .. "+$", "")
    return s
end

local function stringify_header(elem)
    local s = pandoc.utils.stringify(elem)
    -- Сжать любые ASCII-пробелы в один и обрезать края, не трогая cyrillic-байты.
    s = s:gsub(WS .. "+", " ")
    return trim(s)
end

-- Спецразделы, центрируемый prelim-стиль.
local CENTER_HEADERS = {
    ["ВВЕДЕНИЕ"] = true,
    ["ЗАКЛЮЧЕНИЕ"] = true,
    ["СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"] = true,
    ["ПЕРЕЧЕНЬ УСЛОВНЫХ ОБОЗНАЧЕНИЙ И СОКРАЩЕНИЙ"] = true,
}

-- Спецразделы реферата и содержания.
local REFER_HEADERS = {
    ["РЕФЕРАТ"] = true,
    ["СОДЕРЖАНИЕ"] = true,
}

local function header_style(level, txt)
    if level == 1 then
        if CENTER_HEADERS[txt] then
            return "+ЗАГОЛОВОК по центру"
        end
        -- Приложение А/Б/В... тоже на отдельной странице по центру.
        if txt:sub(1, #"ПРИЛОЖЕНИЕ ") == "ПРИЛОЖЕНИЕ " then
            return "+ЗАГОЛОВОК по центру"
        end
        if REFER_HEADERS[txt] then
            return "+ЗаголРеферСодерж"
        end
        return "+Заголовок 1 уровня"
    elseif level == 2 then
        return "+Заголовок 2 уровня"
    elseif level == 3 then
        return "+Заголовок 3 уровня"
    elseif level == 4 then
        return "+Заголовок 4 уровня"
    end
    return nil
end

local function header_to_div(elem)
    -- Pandoc применяет custom-style на Header не к самому заголовку, а к
    -- следующему параграфу. Чтобы стиль гарантированно лёг на текст
    -- заголовка, оборачиваем в Div(Para(content)) с нужным custom-style.
    local txt = stringify_header(elem)
    local style = header_style(elem.level, txt)
    if not style then
        return elem
    end
    local attrs = { ["custom-style"] = style }
    return pandoc.Div(
        { pandoc.Para(elem.content) },
        pandoc.Attr(elem.identifier or "", {}, attrs)
    )
end

-- Подписи рисунков и таблиц используют en-dash (–, U+2013).
-- Прерываем поиск %s на ASCII-варианте, чтобы не зацепить cyrillic-байты.
local FIGURE_PREFIX = "^Рисунок" .. WS .. "+%d+" .. WS .. "+\u{2013}"
local TABLE_PREFIX  = "^Таблица" .. WS .. "+%d+" .. WS .. "+\u{2013}"

local function caption_style(text)
    if text:match(FIGURE_PREFIX) then
        return "+№ - Название рисунка"
    end
    if text:match(TABLE_PREFIX) then
        return "+№ - Название таблицы"
    end
    return nil
end

-- Стиль обычного абзаца основного текста: красная строка 709 twips
-- (1.25 см), без отступа сверху/снизу. Pandoc по умолчанию использует
-- Body Text → Normal, у которого в шаблоне Маршуниной firstLine не задан,
-- поэтому без явного маппинга красной строки не будет.
local BODY_PARAGRAPH_STYLE = "+Абзац с отступом 1-ой строки"

local function wrap_paragraph(elem)
    -- Подпись рисунка/таблицы → свой стиль, не основной абзац.
    local txt = pandoc.utils.stringify(elem)
    local style = caption_style(txt) or BODY_PARAGRAPH_STYLE
    return pandoc.Div(
        { elem },
        pandoc.Attr("", {}, { ["custom-style"] = style })
    )
end

local function refs_blocks_from(ordered_list)
    -- Развернуть OrderedList в плоскую последовательность Div'ов со
    -- стилем "+Список использованных источников". Маркеры списка не нужны —
    -- источники нумеруются вручную в тексте sources.md.
    local out = {}
    for _, item in ipairs(ordered_list.content) do
        for _, sub in ipairs(item) do
            if sub.t == "Para" or sub.t == "Plain" then
                table.insert(out, pandoc.Div(
                    { sub },
                    pandoc.Attr("", {}, { ["custom-style"] = "+Список использованных источников" })
                ))
            else
                table.insert(out, sub)
            end
        end
    end
    return out
end

function Pandoc(doc)
    local new_blocks = {}
    local in_refs = false

    for _, block in ipairs(doc.blocks) do
        if block.t == "Header" then
            local txt = stringify_header(block)
            if block.level == 1 then
                in_refs = (txt == "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ")
            end
            table.insert(new_blocks, header_to_div(block))

        elseif in_refs and block.t == "OrderedList" then
            for _, b in ipairs(refs_blocks_from(block)) do
                table.insert(new_blocks, b)
            end

        elseif block.t == "Para" or block.t == "Plain" then
            table.insert(new_blocks, wrap_paragraph(block))

        else
            table.insert(new_blocks, block)
        end
    end

    doc.blocks = new_blocks
    return doc
end
