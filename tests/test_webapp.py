"""Testes da camada de serviço usada pela interface Web didática."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from minipar.webapp import analyze_source, run_source, run_fork_remote, _run_bounded_process


class WebAppServiceTests(unittest.TestCase):
    def test_test1_examples_are_available_but_remote_fork_is_hidden(self):
        from minipar.webapp import is_web_example, TEST1_EXAMPLES

        self.assertIn("teste01_cliente.mp", TEST1_EXAMPLES)
        self.assertIn("teste01_servidor.mp", TEST1_EXAMPLES)
        self.assertTrue(is_web_example("teste01_cliente.mp"))
        self.assertTrue(is_web_example("teste01_servidor.mp"))
        self.assertTrue(is_web_example("fork_remoto.mp"))


    def test_fork_remoto_inicia_worker_e_executa_tarefa_pela_web(self):
        import socket
        from minipar.webapp import EXAMPLES_DIR

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        source = (EXAMPLES_DIR / "fork_remoto.mp").read_text(encoding="utf-8")
        source = source.replace('"127.0.0.1", 9000', f'"127.0.0.1", {port}')

        result = run_fork_remote(source, timeout=10)

        self.assertTrue(result["ok"], result["stderr"])
        self.assertIn("Fatorial de 10 = 3628800", result["stdout"])
        self.assertIn("Fibonacci: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]", result["stdout"])
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["worker_returncode"], 0)

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
        fake_build = SimpleNamespace(exe_path=Path("programa"))
        timeout_result = {
            "ok": False, "stdout": "saida parcial",
            "stderr": "Execução interrompida após 10 segundos.",
            "returncode": None, "timeout": True, "stage": "run",
        }
        with patch("minipar.webapp.build_executable", return_value=fake_build), \
             patch("minipar.webapp._run_bounded_process", return_value=timeout_result):
            result = run_source('print("teste");')

        self.assertFalse(result["ok"])
        self.assertTrue(result["timeout"])
        self.assertEqual(result["stdout"], "saida parcial")
        self.assertIn("10 segundos", result["stderr"])
        # A resposta precisa continuar serializável pelo endpoint HTTP.
        json.dumps(result, ensure_ascii=False)



    def test_bounded_process_timeout_preserves_partial_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            result = _run_bounded_process(
                [sys.executable, "-c",
                 "import os, time; os.write(1, b'saida parcial\\xff'); "
                 "os.write(2, b'erro parcial'); time.sleep(2)"],
                Path(temp), timeout=0.2,
            )

        self.assertFalse(result["ok"])
        self.assertTrue(result["timeout"])
        self.assertEqual(result["stage"], "run")
        self.assertIn("saida parcial", result["stdout"])
        self.assertIn("\ufffd", result["stdout"])
        self.assertIn("erro parcial", result["stderr"])
        self.assertIn("0.2 segundos", result["stderr"])
        # Bytes arbitrários precisam virar texto UTF-8 serializável no endpoint.
        json.dumps(result, ensure_ascii=False)

    def test_bounded_process_receives_preloaded_stdin(self):
        with tempfile.TemporaryDirectory() as temp:
            result = _run_bounded_process(
                [sys.executable, "-c", "import sys; print(sys.stdin.readline().strip())"],
                Path(temp), timeout=5, stdin_text="((2+4)*7)-(5*4)\n",
            )

        self.assertTrue(result["ok"], result["stderr"])
        self.assertEqual(result["stdout"], "((2+4)*7)-(5*4)\n")

    def test_execution_output_is_capped_across_both_streams(self):
        import minipar.webapp as webapp

        with tempfile.TemporaryDirectory() as temp, \
             patch.object(webapp, "MAX_OUTPUT_BYTES", 128):
            result = _run_bounded_process(
                [sys.executable, "-c",
                 "import sys; sys.stdout.write('x'*10000); "
                 "sys.stderr.write('y'*10000)"],
                Path(temp), timeout=5,
            )

        self.assertFalse(result["ok"])
        self.assertTrue(result["output_limit"])
        notice = "Saída interrompida: limite de 0 KiB atingido."
        self.assertTrue(result["stderr"].endswith(notice))
        captured_stderr = result["stderr"][:-len(notice)].removesuffix("\n")
        self.assertLessEqual(
            len(result["stdout"].encode()) + len(captured_stderr.encode()),
            128,
        )

    def test_compilation_timeout_returns_distinct_stage(self):
        timeout_error = subprocess.TimeoutExpired(cmd=["g++"], timeout=20)
        with patch("minipar.webapp.build_executable", side_effect=timeout_error):
            result = run_source('print("teste");')

        self.assertFalse(result["ok"])
        self.assertTrue(result["timeout"])
        self.assertEqual(result["stage"], "compile")
        self.assertIn("20 segundos", result["stderr"])
        json.dumps(result, ensure_ascii=False)

    def test_compilation_error_returns_json_friendly_result(self):
        with patch("minipar.webapp.build_executable", side_effect=RuntimeError("erro do compilador")):
            result = run_source('print("teste");')

        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "compile")
        self.assertIn("erro do compilador", result["stderr"])
        json.dumps(result, ensure_ascii=False)

    def test_local_request_rejects_non_loopback_host(self):
        from minipar.webapp import MiniParHandler

        handler = MiniParHandler.__new__(MiniParHandler)
        handler.headers = {"Host": "example.com:8765"}
        self.assertFalse(handler._is_local_request())

    def test_local_request_rejects_missing_origin(self):
        from minipar.webapp import MiniParHandler

        handler = MiniParHandler.__new__(MiniParHandler)
        handler.headers = {
            "Host": "127.0.0.1:8765",
            "Sec-Fetch-Site": "same-origin",
        }
        self.assertFalse(handler._is_local_request())

    def test_web_limits_concurrent_runs(self):
        from minipar.webapp import MAX_CONCURRENT_RUNS, _RUN_SLOTS

        acquired = []
        try:
            for _ in range(MAX_CONCURRENT_RUNS):
                acquired.append(_RUN_SLOTS.acquire(blocking=False))
            self.assertTrue(all(acquired))
            self.assertFalse(_RUN_SLOTS.acquire(blocking=False))
        finally:
            for held in acquired:
                if held:
                    _RUN_SLOTS.release()

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
