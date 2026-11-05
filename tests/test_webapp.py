"""Testes da camada de serviço usada pela interface Web didática."""
import json
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from minipar.webapp import analyze_source, run_source


class WebAppServiceTests(unittest.TestCase):
    def test_pipeline_returns_all_compilation_stages(self):
        result = analyze_source('var numero = 7;\nprint("Resultado:", numero * 6);')
        self.assertTrue(result["ok"], result["errors"])
        for stage in ("lexer", "parser", "semantic", "tac", "cpp"):
            self.assertEqual(result["stages"][stage], "ok")
        self.assertTrue(result["tokens"])
        self.assertEqual(result["ast"]["type"], "Program")
        self.assertIn("print", result["tac"])
        self.assertIn("main", result["cpp"])

    def test_lexical_error_stops_later_stages(self):
        result = analyze_source("var x = @;")
        self.assertFalse(result["ok"])
        self.assertEqual(result["stages"]["lexer"], "error")
        self.assertEqual(result["stages"]["semantic"], "pending")
        self.assertTrue(result["errors"])

    def test_semantic_error_prevents_codegen(self):
        result = analyze_source("var x = 1;\nx = true;")
        self.assertFalse(result["ok"])
        self.assertEqual(result["stages"]["semantic"], "error")
        self.assertEqual(result["stages"]["tac"], "pending")
        self.assertEqual(result["cpp"], "")

    def test_execution_timeout_preserves_partial_byte_output_as_json_text(self):
        timeout_error = subprocess.TimeoutExpired(
            cmd=["programa"], timeout=10, output=b"saida parcial"
        )
        fake_build = SimpleNamespace(exe_path=Path("programa"))
        with patch("minipar.webapp.build_executable", return_value=fake_build), \
             patch("minipar.webapp.subprocess.run", side_effect=timeout_error):
            result = run_source('print("teste");')

        self.assertFalse(result["ok"])
        self.assertTrue(result["timeout"])
        self.assertEqual(result["stdout"], "saida parcial")
        self.assertIn("10 segundos", result["stderr"])
        # A resposta precisa continuar serializável pelo endpoint HTTP.
        json.dumps(result, ensure_ascii=False)



    def test_local_request_rejects_non_loopback_host(self):
        from minipar.webapp import MiniParHandler

        handler = MiniParHandler.__new__(MiniParHandler)
        handler.headers = {"Host": "example.com:8765"}
        self.assertFalse(handler._is_local_request())

    def test_local_request_rejects_cross_origin(self):
        from minipar.webapp import MiniParHandler

        handler = MiniParHandler.__new__(MiniParHandler)
        handler.headers = {
            "Host": "127.0.0.1:8765",
            "Origin": "http://evil.example",
            "Sec-Fetch-Site": "cross-site",
        }
        self.assertFalse(handler._is_local_request())

    def test_local_request_accepts_same_origin_loopback(self):
        from minipar.webapp import MiniParHandler

        handler = MiniParHandler.__new__(MiniParHandler)
        handler.headers = {
            "Host": "127.0.0.1:8765",
            "Origin": "http://127.0.0.1:8765",
            "Sec-Fetch-Site": "same-origin",
        }
        self.assertTrue(handler._is_local_request())

if __name__ == "__main__":
    unittest.main()
