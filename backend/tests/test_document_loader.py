import os
import pytest
from backend.app.rag.document_loader import FileParser, load_and_split_document

def test_parse_txt(tmp_path):
    # Create a temporary txt file
    test_content = "这是测试商品知识库的内容。测试分词与读取逻辑。"
    test_file = tmp_path / "test_product.txt"
    test_file.write_text(test_content, encoding="utf-8")
    
    # Parse file
    parsed_text = FileParser.parse_txt(str(test_file))
    assert parsed_text == test_content

def test_load_and_split_document(tmp_path):
    # Create temporary markdown file
    content = "商品名称：小米手机14\n规格参数：16GB+512GB\n" + "测试段落。" * 200 # long content to force splitting
    test_file = tmp_path / "xiaomi14.md"
    test_file.write_text(content, encoding="utf-8")
    
    # Load and split
    document_id = "test-doc-id-xyz"
    chunks = load_and_split_document(str(test_file), "xiaomi14.md", document_id)
    
    # 1. Chunks should be a list of LangChain documents
    assert len(chunks) > 1
    
    # 2. Check metadata
    for chunk in chunks:
        assert chunk.metadata["document_id"] == document_id
        assert chunk.metadata["source_name"] == "xiaomi14.md"
        assert "chunk_id" in chunk.metadata
        assert len(chunk.page_content) <= 600 # chunk_size in loader is 600
