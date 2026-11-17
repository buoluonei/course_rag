from dataclasses import dataclass
import re
@dataclass
class DocumentBlock:
    text:str
    section_title:str|None=None
    page_number:int|None=None
    
@dataclass
class Chunk:
    text:str
    chunk_index:int
    section_title:str|None=None
    page_number:int|None=None
    
HEADING_PATTERNS=[
    re.compile(r"^#{1,6}\s+\S+"),
    re.compile(r"^第[一二三四五六七八九十\d]+章\s*\S*"),
    re.compile(r"^[一二三四五六七八九十]+、\s*\S+"),
    re.compile(r"^\d+(?:\.\d+)+\s*\S+")
]   
    
def is_heading(text:str)->bool:
    return any(pattern.match(text) for pattern in HEADING_PATTERNS)

def clean_heading(text:str)->str:
    return text.lstrip("#").strip()
    
def text_to_blocks(text:str,page_number:int|None=None)->list[DocumentBlock]:
    parts=re.split(r"\n\s*\n",text)
    
    blocks=[]
    current_section=None
    
    for part in parts:
        part=part.strip()
        if not part:
            continue
        lines=[line.strip() for line in part.splitlines() if line.strip()]
        
        if len(lines)==1 and is_heading(lines[0]):
            current_section=clean_heading(lines[0])
            continue
        if len(lines)>=2 and is_heading(lines[0]):
            current_section=clean_heading(lines[0])
            part="\n".join(lines[1:]).strip()
        if part:
            blocks.append(DocumentBlock(text=part,section_title=current_section,page_number=page_number))
    return blocks

def split_long_text(text:str,chunk_size:int,chunk_overlap:int)->list[str]:
    if chunk_size<=0:
        raise ValueError("chunk_size必须大于0")
    if chunk_overlap<0 or chunk_overlap>=chunk_size:
        raise ValueError("chunk_overlap必须大于等于0且小于chunk_size")
    chunks=[]
    step=chunk_size-chunk_overlap
    start=0
    while start<len(text):
        if start+chunk_size<len(text):
            chunks.append(text[start:start+chunk_size].strip())
            start+=step
        else:
            chunks.append(text[start:].strip())
            break
    return chunks

def chunk_document(blocks:list[DocumentBlock],chunk_size:int=200,chunk_overlap=40)->list[Chunk]:
    result=[]
    buffer=[]
    buffer_length=0
    buffer_section=None
    buffer_page=None
    def flush_chunk():
        nonlocal buffer,buffer_length,buffer_section,buffer_page
        if not buffer:
            return
        result.append(Chunk(
            text="\n\n".join(buffer),
            chunk_index=len(result),
            section_title=buffer_section,
            page_number=buffer_page
        ))
        buffer=[]
        buffer_length=0
        buffer_section=None
        buffer_page=None
    for block in blocks:
        text=block.text
        if not text:
            continue
        if buffer and (buffer_section!=block.section_title or buffer_page!=block.page_number):
            flush_chunk()
        if len(text) > chunk_size:
            flush_chunk()
            for piece in split_long_text(text,chunk_size=chunk_size,chunk_overlap=chunk_overlap):
                result.append(Chunk(text=piece,chunk_index=len(result),section_title=block.section_title,page_number=block.page_number))
            continue
        additional_length=len(text)
        if buffer:
            additional_length+=2
        if buffer and buffer_length+additional_length>chunk_size:
            flush_chunk()
        if buffer_section is None:
            buffer_section=block.section_title
        if buffer_page is None:
            buffer_page=block.page_number
        buffer.append(text)
        buffer_length+=additional_length
    
    flush_chunk()
    return result
        
