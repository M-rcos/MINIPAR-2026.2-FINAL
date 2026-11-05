"""Testes da camada de serviço usada pela interface Web didática."""
import unittest
from minipar.webapp import analyze_source

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

if __name__ == "__main__":
    unittest.main()
