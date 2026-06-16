import unittest

from core.document.ingest import DocumentParseError, extract_keywords, parse_document_bytes


class TestDocumentIngest(unittest.TestCase):
    def test_parse_markdown(self):
        data = b"# Title\n\nHello **world** from CNexus ingest."
        out = parse_document_bytes("notes.md", data)
        self.assertEqual(out["format"], "text")
        self.assertIn("Hello", out["text"])
        self.assertGreater(out["char_count"], 0)
        self.assertIsInstance(out["keywords"], list)

    def test_parse_txt_truncates(self):
        data = ("alpha " * 2000).encode("utf-8")
        out = parse_document_bytes("long.txt", data, max_chars=100)
        self.assertTrue(out["truncated"])
        self.assertEqual(out["char_count"], 100)

    def test_empty_file_rejected(self):
        with self.assertRaises(DocumentParseError) as ctx:
            parse_document_bytes("empty.txt", b"")
        self.assertEqual(ctx.exception.code, "empty_file")

    def test_legacy_doc_rejected(self):
        with self.assertRaises(DocumentParseError) as ctx:
            parse_document_bytes("legacy.doc", b"fake")
        self.assertEqual(ctx.exception.code, "legacy_doc_unsupported")

    def test_extract_keywords_mixed(self):
        words = extract_keywords("机器学习 machine learning 深度学习 machine")
        self.assertIn("machine", words)
        self.assertTrue(any("学习" in w for w in words))


if __name__ == "__main__":
    unittest.main()
