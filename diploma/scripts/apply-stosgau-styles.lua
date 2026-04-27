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

-- Стиль таблицы из шаблона Маршуниной: 'Table Grid' (styleId 938) даёт
-- чёрные тонкие границы вокруг каждой ячейки. Без явного маппинга pandoc
-- использует 'Normal Table' без границ.
--
-- Pandoc для таблиц прокидывает значение custom-style в <w:tblStyle w:val="..."/>
-- ВЕРБАТИМ, а Word резолвит этот атрибут по w:styleId, а не по w:name.
-- Поэтому здесь указан именно styleId "938" из template/blank-template.docx,
-- а не человекочитаемое имя "Table Grid".
local TABLE_STYLE = "938"

-- Стиль абзаца внутри ячейки таблицы: '+Текст в таблице' (styleId 989)
-- задаёт одинарный интервал и Times New Roman 12, без красной строки.
local CELL_PARAGRAPH_STYLE = "+Текст в таблице"

local function wrap_cell_paragraph(elem)
    return pandoc.Div(
        { elem },
        pandoc.Attr("", {}, { ["custom-style"] = CELL_PARAGRAPH_STYLE })
    )
end

local function process_cell(cell)
    local new_contents = {}
    for _, b in ipairs(cell.contents) do
        if b.t == "Para" or b.t == "Plain" then
            table.insert(new_contents, wrap_cell_paragraph(b))
        else
            table.insert(new_contents, b)
        end
    end
    cell.contents = new_contents
    return cell
end

local function process_row(row)
    local new_cells = {}
    for _, c in ipairs(row.cells) do
        table.insert(new_cells, process_cell(c))
    end
    row.cells = new_cells
    return row
end

local function process_rows_inplace(rows)
    if not rows then return end
    for i, r in ipairs(rows) do
        rows[i] = process_row(r)
    end
end

local function process_table(tbl)
    -- Применить custom-style на саму таблицу, чтобы pandoc положил
    -- <w:tblStyle w:val="938"/> в word/document.xml.
    tbl.attr.attributes["custom-style"] = TABLE_STYLE

    -- Обработать все строки таблицы (header, body, footer) — заменить
    -- Para/Plain внутри ячеек на Div с custom-style "+Текст в таблице".
    if tbl.head then
        process_rows_inplace(tbl.head.rows)
    end
    for _, body in ipairs(tbl.bodies) do
        process_rows_inplace(body.head)
        process_rows_inplace(body.body)
    end
    if tbl.foot then
        process_rows_inplace(tbl.foot.rows)
    end
    return tbl
end

local function wrap_paragraph(elem)
    -- Подпись рисунка/таблицы → свой стиль, не основной абзац.
    local txt = pandoc.utils.stringify(elem)
    local style = caption_style(txt) or BODY_PARAGRAPH_STYLE
    return pandoc.Div(
        { elem },
        pandoc.Attr("", {}, { ["custom-style"] = style })
    )
end

-- По СТО СГАУ перечни оформляются обычными абзацами с дефисом перед элементом,
-- без маркеров-кружочков и без автонумерации Word. Поэтому BulletList разворачиваем
-- в плоскую последовательность Div'ов со стилем основного абзаца, а первый инлайн
-- каждого элемента дополняем префиксом "– " (en-dash + пробел).
local function bulletlist_to_blocks(bl)
    local out = {}
    for _, item in ipairs(bl.content) do
        for _, sub in ipairs(item) do
            if sub.t == "Para" or sub.t == "Plain" then
                local inlines = sub.content
                table.insert(inlines, 1, pandoc.Space())
                table.insert(inlines, 1, pandoc.Str("\u{2013}"))
                table.insert(out, pandoc.Div(
                    { pandoc.Para(inlines) },
                    pandoc.Attr("", {}, { ["custom-style"] = BODY_PARAGRAPH_STYLE })
                ))
            elseif sub.t == "BulletList" then
                for _, b in ipairs(bulletlist_to_blocks(sub)) do
                    table.insert(out, b)
                end
            else
                table.insert(out, sub)
            end
        end
    end
    return out
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

        elseif block.t == "BulletList" then
            for _, b in ipairs(bulletlist_to_blocks(block)) do
                table.insert(new_blocks, b)
            end

        elseif block.t == "Para" or block.t == "Plain" then
            table.insert(new_blocks, wrap_paragraph(block))

        elseif block.t == "Table" then
            table.insert(new_blocks, process_table(block))

        else
            table.insert(new_blocks, block)
        end
    end

    doc.blocks = new_blocks
    return doc
end
