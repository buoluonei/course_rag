from io import BytesIO
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from docx import Document
from pathlib import Path

class DocumentParseError(Exception):
    pass

def _parse_txt(content_bytes):
    try:
        return content_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DocumentParseError("TXT文件必须使用UTF-8编码") from error
    
def _parse_pdf(content_bytes):
    try:
        reader=PdfReader(BytesIO(content_bytes))
        if reader.is_encrypted:
            raise DocumentParseError("暂不支持加密PDF")
        pages=[page.extract_text() or "" for page in reader.pages]
    except (ValueError,PdfReadError) as error:
        raise DocumentParseError("PDF文件已经损坏或无法读取") from error
    text="\n\n".join(pages).strip()
    if not text:
        raise DocumentParseError("PDF 中没有可提取文字，扫描版 PDF 暂不支持")
    return text

def _parse_docx(content_bytes):
    try:
        document=Document(BytesIO(content_bytes))
    except Exception as error:
        raise DocumentParseError("DOCX文件已经损坏或无法读取") from error
    
    parts=[]
    for paragraph in document.paragraphs:
        text=paragraph.text.strip()
        if text:
            parts.append(text)
    
    for table in document.tables:
        for row in table.rows:
            cells=[cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append("|".join(cells))
    
    text="\n".join(parts).strip()
    if not text:
        raise DocumentParseError("DOCX没有可提取文字")
    return text

def parse_document(filename,content_bytes):
    extension=Path(filename).suffix.lower()
    parsers={".txt":_parse_txt,
             ".pdf":_parse_pdf,
             ".docx":_parse_docx}
    parser=parsers.get(extension)
    if parser is None:
        raise DocumentParseError("只支持pdf,docx,txt文件")
    return parser(content_bytes)
        