from __future__ import annotations

from app.rag.chunker import TextChunker
from app.rag.parsers.base import ParsedDocument, ParsedSection, ParsedTable


def test_text_chunker_chunks_parsed_document_and_keeps_metadata() -> None:
    parsed = ParsedDocument(
        title="售后政策",
        source_type="upload",
        mime_type="text/plain",
        sections=[
            ParsedSection(
                title="退货规则",
                text="七天无理由退货。商品未拆封且不影响二次销售，可以申请退货。",
                page_no=1,
                metadata={
                    "parser_quality": "native_text",
                },
            )
        ],
        metadata={
            "filename": "policy.txt",
            "parser": "TextDocumentParser",
        },
    )

    chunker = TextChunker(chunk_size=30, chunk_overlap=5)

    chunks = chunker.chunk_document(
        document_id=None,
        parsed_document=parsed,
    )

    assert chunks
    assert chunks[0].chunk_no == 1
    assert chunks[0].page_no == 1
    assert chunks[0].section_title == "退货规则"
    assert chunks[0].keywords
    assert chunks[0].metadata["parser_quality"] == "native_text"
    assert chunks[0].metadata["filename"] == "policy.txt"


def test_parsed_table_can_convert_to_markdown() -> None:
    table = ParsedTable(
        rows=[
            ["条件", "说明"],
            ["未拆封", "支持退货"],
        ],
        caption="退货规则表",
    )

    markdown = table.to_markdown()

    assert "| 条件 | 说明 |" in markdown
    assert "| --- | --- |" in markdown
    assert "| 未拆封 | 支持退货 |" in markdown


def test_text_chunker_includes_table_markdown_in_content() -> None:
    parsed = ParsedDocument(
        title="表格政策",
        source_type="upload",
        sections=[
            ParsedSection(
                title="退货表",
                text="以下是退货规则。",
                tables=[
                    ParsedTable(
                        rows=[
                            ["条件", "说明"],
                            ["未拆封", "支持退货"],
                        ],
                        caption="退货规则表",
                    )
                ],
                metadata={
                    "parser_quality": "docx_text_table",
                },
            )
        ],
    )

    chunker = TextChunker(chunk_size=500, chunk_overlap=50)

    chunks = chunker.chunk_document(
        document_id=None,
        parsed_document=parsed,
    )

    assert chunks
    assert "退货规则表" in chunks[0].content
    assert "| 条件 | 说明 |" in chunks[0].content
    assert "未拆封" in chunks[0].content