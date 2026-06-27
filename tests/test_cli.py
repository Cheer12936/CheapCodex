import tempfile
import unittest
from pathlib import Path

from codex_cheap_worker.cli import build_corpus, read_payloads, redact_text, resolve_paths


class CliHelpersTest(unittest.TestCase):
    def test_resolve_paths_supports_globs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("print('a')", encoding="utf-8")
            (root / "b.txt").write_text("b", encoding="utf-8")

            paths = resolve_paths([str(root / "*.py")])

            self.assertEqual([p.name for p in paths], ["a.py"])

    def test_redact_text_masks_common_secret_lines(self):
        text = "WORKER_API_KEY=sk-1234567890abcdef\nplain=value"

        redacted = redact_text(text)

        self.assertIn("WORKER_API_KEY=[REDACTED]", redacted)
        self.assertIn("plain=value", redacted)

    def test_read_payloads_skips_binary_and_builds_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text_path = root / "source.py"
            bin_path = root / "image.bin"
            text_path.write_text("def f():\n    return 1\n", encoding="utf-8")
            bin_path.write_bytes(b"\x00\x01\x02")

            payloads = read_payloads([text_path, bin_path])
            corpus = build_corpus(payloads, line_numbers=True)

            self.assertEqual(len(payloads), 1)
            self.assertIn("source.py", corpus)
            self.assertIn("1: def f():", corpus)


if __name__ == "__main__":
    unittest.main()

