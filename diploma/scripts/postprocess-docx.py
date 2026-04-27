"""Post-обработка собранного pandoc'ом docx.

Pandoc для каждого параграфа внутри ячеек таблицы навязывает встроенный
стиль "Compact", игнорируя custom-style, прокинутый через Lua-фильтр на
уровне Div. Этот пост-шаг подменяет ссылки <w:pStyle w:val="Compact"/>
внутри document.xml на styleId "989" — стиль "+Текст в таблице" из
template/blank-template.docx.

Использование: python scripts/postprocess-docx.py <docx>
"""
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


CELL_PARAGRAPH_STYLE_ID = "989"


def postprocess(docx_path: Path) -> int:
    if not docx_path.exists():
        print(f"[postprocess] нет файла: {docx_path}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(docx_path, "r") as z:
        names = z.namelist()
        with z.open("word/document.xml") as f:
            doc_xml = f.read().decode("utf-8")
        files = {n: z.read(n) for n in names}

    new_doc_xml = doc_xml
    for token in (
        '<w:pStyle w:val="Compact" />',
        '<w:pStyle w:val="Compact"/>',
    ):
        new_doc_xml = new_doc_xml.replace(
            token, f'<w:pStyle w:val="{CELL_PARAGRAPH_STYLE_ID}" />'
        )

    replaced = doc_xml.count("Compact") - new_doc_xml.count("Compact")
    if replaced == 0:
        print("[postprocess] пСтиль Compact не найден, постобработка не нужна.")
        return 0

    files["word/document.xml"] = new_doc_xml.encode("utf-8")

    import os
    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".docx", dir=str(docx_path.parent))
    os.close(tmp_fd)
    Path(tmp_name).unlink()
    try:
        with zipfile.ZipFile(tmp_name, "w", zipfile.ZIP_DEFLATED) as zout:
            for n in names:
                zout.writestr(n, files[n])
        shutil.move(tmp_name, str(docx_path))
    except Exception:
        if Path(tmp_name).exists():
            Path(tmp_name).unlink()
        raise

    print(f"[postprocess] заменено пСтилей Compact -> {CELL_PARAGRAPH_STYLE_ID}: {replaced}")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/postprocess-docx.py <docx>", file=sys.stderr)
        return 2
    return postprocess(Path(sys.argv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
