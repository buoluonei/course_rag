# PDF and DOCX Upload Implementation Plan

> **For agentic workers:** Implement this plan inline and verify each supported format locally.

**Goal:** Extend the independent RAG demo so one upload endpoint accepts TXT, PDF, and DOCX course materials.

**Architecture:** A focused document parser converts each supported file type into plain text. The existing upload route validates the result, chunks it, and stores it without changing the retrieval or question-answer flow.

**Tech Stack:** FastAPI, pypdf, python-docx, MySQL

---

### Task 1: Document parser

**Files:**
- Create: `demo_app/document_parser.py`

- [ ] Parse UTF-8 TXT bytes.
- [ ] Extract text from each PDF page.
- [ ] Extract DOCX paragraphs and table cells.
- [ ] Return clear errors for unsupported, damaged, encrypted, or image-only documents.

### Task 2: Upload integration

**Files:**
- Modify: `demo_app/main.py`
- Modify: `requirements.txt`

- [ ] Send uploaded bytes and filename to the parser.
- [ ] Keep the existing chunking and database replacement flow.
- [ ] Update the web file picker and user-facing text.

### Task 3: Verification and documentation

**Files:**
- Modify: `demo_app/README.md`

- [ ] Generate local TXT, PDF, and DOCX samples.
- [ ] Verify each format uploads and produces chunks.
- [ ] Verify unsupported and image-only files return useful errors.
