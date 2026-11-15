"""Interface Web didática local do MiniPar 2026.2."""
from __future__ import annotations
import argparse, ipaddress, json, os, re, signal, subprocess, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from .codegen import build_executable
from .lexer import Lexer
from .parser import Parser, to_dict
from .semantic import SemanticAnalyzer
from .tac import TACGenerator
from .pipeline import to_cpp

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR, EXAMPLES_DIR = ROOT / "web", ROOT / "exemplos"
WEB_EXCLUDED_EXAMPLES = frozenset()
TEST1_EXAMPLES = frozenset({"teste01_cliente.mp", "teste01_servidor.mp"})


def is_web_example(name: str) -> bool:
    """Informa se um exemplo pode ser disponibilizado pela interface Web."""
    return name not in WEB_EXCLUDED_EXAMPLES
MAX_SOURCE_BYTES = 128 * 1024
MAX_STDIN_BYTES = 64 * 1024
MAX_REQUEST_BYTES = 6 * (MAX_SOURCE_BYTES + MAX_STDIN_BYTES) + 4096
COMPILE_TIMEOUT_SECONDS = 20
RUN_TIMEOUT_SECONDS = 10
MAX_CONCURRENT_RUNS = 2
MAX_OUTPUT_BYTES = 1024 * 1024
_OUTPUT_CHUNK_BYTES = 8192
_RUN_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_RUNS)
_TEST1_SLOT = threading.BoundedSemaphore(1)

def analyze_source(source: str) -> dict:
    """Executa as fases em ordem e devolve dados serializáveis para a UI."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    tree = parser.parse()
    errors = sorted([*lexer.errors, *parser.errors], key=lambda e: (e.line, e.col))
    result = {
        "ok": not errors,
        "tokens": [t.to_dict() for t in tokens if t.type != "EOF"],
        "ast": to_dict(tree), "ast_text": "", "symbols": [],
        "tac": "", "cpp": "", "errors": [e.to_dict() for e in errors],
        "stages": {"lexer": "ok" if not lexer.errors else "error",
                   "parser": "ok" if not parser.errors else "error",
                   "semantic": "pending", "tac": "pending", "cpp": "pending"},
    }
    if errors:
        result["ast_text"] = "AST parcial: corrija os erros léxicos/sintáticos."
        return result
    analyzer = SemanticAnalyzer()
    analyzer.analyze(tree)
    semantic_errors = sorted(analyzer.errors, key=lambda e: (e.line, e.col))
    result["symbols"] = analyzer.symbol_table.to_dict()
    result["errors"] = [e.to_dict() for e in semantic_errors]
    result["stages"]["semantic"] = "error" if semantic_errors else "ok"
    if semantic_errors:
        result["ok"] = False
        return result
    from .parser.ast_printer import format_tree
    result["ast_text"] = format_tree(tree)
    tac_program = TACGenerator(analyzer).generate(tree)
    result["tac"] = tac_program.format()
    result["stages"]["tac"] = "ok"
    result["cpp"] = to_cpp(source)
    result["stages"]["cpp"] = "ok"
    result["ok"] = True
    return result

def _stop_process_tree(proc: subprocess.Popen) -> None:
    """Encerra o processo e, em POSIX, todo o grupo iniciado para ele."""
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except ProcessLookupError:
        pass
    except OSError:
        try:
            proc.kill()
        except OSError:
            pass


def _run_bounded_process(
    command: list[str], cwd: Path, timeout: int, stdin_text: str = ""
) -> dict:
    """Executa com stdin pré-carregado, drenando a saída e limitando seus bytes."""
    proc = subprocess.Popen(
        command, cwd=cwd, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        bufsize=0, start_new_session=(os.name == "posix"),
    )
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    state = {"total": 0, "limit": False}
    lock = threading.Lock()

    def drain(pipe, key):
        try:
            while True:
                chunk = pipe.read(_OUTPUT_CHUNK_BYTES)
                if not chunk:
                    break
                with lock:
                    remaining = MAX_OUTPUT_BYTES - state["total"]
                    if remaining > 0:
                        kept = chunk[:remaining]
                        captured[key].extend(kept)
                        state["total"] += len(kept)
                    if len(chunk) > max(remaining, 0):
                        state["limit"] = True
                if state["limit"]:
                    _stop_process_tree(proc)
        finally:
            pipe.close()

    def feed_stdin():
        try:
            if proc.stdin is not None:
                proc.stdin.write(stdin_text.encode("utf-8"))
                proc.stdin.flush()
        except (BrokenPipeError, OSError):
            # O programa pode terminar sem consumir toda a entrada.
            pass
        finally:
            if proc.stdin is not None:
                proc.stdin.close()

    readers = [
        threading.Thread(target=drain, args=(proc.stdout, "stdout"), daemon=True),
        threading.Thread(target=drain, args=(proc.stderr, "stderr"), daemon=True),
    ]
    for reader in readers:
        reader.start()
    stdin_writer = threading.Thread(target=feed_stdin, daemon=True)
    stdin_writer.start()

    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _stop_process_tree(proc)
        proc.wait()

    stdin_writer.join()
    for reader in readers:
        reader.join()

    stdout = bytes(captured["stdout"]).decode("utf-8", errors="replace")
    stderr = bytes(captured["stderr"]).decode("utf-8", errors="replace")
    if timed_out:
        stderr = (stderr + f"\nExecução interrompida após {timeout} segundos.").strip()
        return {"ok": False, "stdout": stdout, "stderr": stderr,
                "returncode": None, "timeout": True, "stage": "run"}
    if state["limit"]:
        notice = f"Saída interrompida: limite de {MAX_OUTPUT_BYTES // 1024} KiB atingido."
        stderr = (stderr + "\n" + notice).strip()
        return {"ok": False, "stdout": stdout, "stderr": stderr,
                "returncode": proc.returncode, "output_limit": True}
    return {"ok": proc.returncode == 0, "stdout": stdout,
            "stderr": stderr, "returncode": proc.returncode}


def run_source(
    source: str, timeout: int = RUN_TIMEOUT_SECONDS, stdin_text: str = ""
) -> dict:
    """Compila e executa em pasta temporária, com entrada stdin opcional."""
    with tempfile.TemporaryDirectory(prefix="minipar-web-") as temp:
        work = Path(temp)
        path = work / "programa.mp"
        path.write_text(source, encoding="utf-8")
        try:
            build = build_executable(str(path), out_dir=str(work / "build"),
                                     timeout=COMPILE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "",
                    "stderr": f"Compilação interrompida após {COMPILE_TIMEOUT_SECONDS} segundos.",
                    "returncode": None, "timeout": True, "stage": "compile"}
        except Exception as exc:
            return {"ok": False, "stdout": "", "stderr": str(exc),
                    "returncode": None, "stage": "compile"}
        try:
            return _run_bounded_process(
                [str(build.exe_path.resolve())], work, timeout, stdin_text=stdin_text
            )
        except Exception as exc:
            return {"ok": False, "stdout": "", "stderr": str(exc), "returncode": None}


def run_fork_remote(source: str, timeout: int = RUN_TIMEOUT_SECONDS) -> dict:
    """Executa fork remoto em localhost iniciando e encerrando um worker temporário."""
    ports = re.findall(
        r'\bon\s+host\s+"127\.0\.0\.1"\s*,\s*(\d+)',
        source,
    )
    if len(ports) != 1:
        return {
            "ok": False, "stdout": "",
            "stderr": "O exemplo precisa declarar exatamente uma tarefa remota em 127.0.0.1 com uma porta explícita.",
            "returncode": None, "stage": "input",
        }
    port = int(ports[0])
    if not 1 <= port <= 65535:
        return {"ok": False, "stdout": "", "stderr": "Porta do worker inválida.",
                "returncode": None, "stage": "input"}

    with tempfile.TemporaryDirectory(prefix="minipar-web-fork-") as temp:
        work = Path(temp)
        path = work / "fork_remoto.mp"
        path.write_text(source, encoding="utf-8")
        try:
            build = build_executable(
                str(path), out_dir=str(work / "build"),
                timeout=COMPILE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "",
                    "stderr": f"Compilação interrompida após {COMPILE_TIMEOUT_SECONDS} segundos.",
                    "returncode": None, "timeout": True, "stage": "compile"}
        except Exception as exc:
            return {"ok": False, "stdout": "", "stderr": str(exc),
                    "returncode": None, "stage": "compile"}

        worker = None
        worker_output = {"stdout": bytearray(), "stderr": bytearray()}
        worker_state = {"total": 0, "limit": False}
        lock = threading.Lock()
        ready = threading.Event()
        readers = []

        def drain_worker(pipe, key):
            marker = f"trabalhador aguardando tarefas na porta {port}".encode()
            tail = b""
            try:
                while True:
                    chunk = pipe.read(_OUTPUT_CHUNK_BYTES)
                    if not chunk:
                        break
                    if key == "stderr" and marker in tail + chunk:
                        ready.set()
                    tail = (tail + chunk)[-max(len(marker), 64):]
                    with lock:
                        remaining = MAX_OUTPUT_BYTES - worker_state["total"]
                        if remaining > 0:
                            kept = chunk[:remaining]
                            worker_output[key].extend(kept)
                            worker_state["total"] += len(kept)
                        if len(chunk) > max(remaining, 0):
                            worker_state["limit"] = True
            finally:
                pipe.close()

        try:
            worker = subprocess.Popen(
                [str(build.exe_path.resolve()), "--worker", str(port), "--worker-bind", "127.0.0.1", "--worker-tasks", "1"],
                cwd=work, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
                start_new_session=(os.name == "posix"),
            )
            readers = [
                threading.Thread(target=drain_worker, args=(worker.stdout, "stdout"), daemon=True),
                threading.Thread(target=drain_worker, args=(worker.stderr, "stderr"), daemon=True),
            ]
            for reader in readers:
                reader.start()

            if not ready.wait(timeout=3):
                if worker.poll() is None:
                    _stop_process_tree(worker)
                    worker.wait()
                for reader in readers:
                    reader.join(timeout=2)
                worker_err = bytes(worker_output["stderr"]).decode("utf-8", errors="replace")
                detail = worker_err.strip() or f"O worker não abriu a porta {port} em 3 segundos."
                return {"ok": False, "stdout": "", "stderr": detail,
                        "returncode": worker.returncode, "stage": "worker"}

            main_result = _run_bounded_process(
                [str(build.exe_path.resolve())], work, timeout
            )

            worker_stopped = True
            if main_result.get("timeout"):
                worker_stopped = False
            else:
                try:
                    worker.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    worker_stopped = False

            if worker.poll() is None:
                _stop_process_tree(worker)
                worker.wait()
            for reader in readers:
                reader.join(timeout=2)

            worker_out = bytes(worker_output["stdout"]).decode("utf-8", errors="replace")
            worker_err = bytes(worker_output["stderr"]).decode("utf-8", errors="replace")
            stdout = main_result.get("stdout", "")
            if worker_out:
                stdout = (stdout + "\n=== Worker remoto ===\n" + worker_out).strip()
            stderr_parts = [part for part in (main_result.get("stderr", ""), worker_err) if part]
            if not worker_stopped:
                stderr_parts.append("O worker não encerrou normalmente após a tarefa remota.")
            if worker_state["limit"]:
                stderr_parts.append("A saída do worker ultrapassou o limite permitido.")
            ok = (main_result.get("ok", False) and worker_stopped
                  and worker.returncode == 0 and not worker_state["limit"])
            return {
                "ok": ok, "stdout": stdout, "stderr": "\n".join(stderr_parts),
                "returncode": main_result.get("returncode"),
                "worker_returncode": worker.returncode,
                "timeout": main_result.get("timeout", False),
                "output_limit": main_result.get("output_limit", False) or worker_state["limit"],
            }
        except Exception as exc:
            return {"ok": False, "stdout": "", "stderr": str(exc),
                    "returncode": None, "stage": "run"}
        finally:
            if worker is not None and worker.poll() is None:
                _stop_process_tree(worker)
                worker.wait()
            for reader in readers:
                reader.join(timeout=2)



def run_test1(source: str, example: str, stdin_text: str = "",
              timeout: int = RUN_TIMEOUT_SECONDS) -> dict:
    """Executa o Teste 1 localmente: servidor e cliente em processos separados."""
    if example not in TEST1_EXAMPLES:
        return {"ok": False, "stdout": "", "stderr": "Exemplo inválido para o Teste 1.",
                "returncode": None, "stage": "run"}
    if not any(line.strip() == "sair" for line in stdin_text.splitlines()):
        return {"ok": False, "stdout": "",
                "stderr": "Inclua 'sair' em uma linha da entrada para encerrar a comunicação.",
                "returncode": None, "stage": "input"}

    client_path = EXAMPLES_DIR / "teste01_cliente.mp"
    server_path = EXAMPLES_DIR / "teste01_servidor.mp"
    try:
        client_source = source if example == "teste01_cliente.mp" else client_path.read_text(encoding="utf-8")
        server_source = source if example == "teste01_servidor.mp" else server_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc),
                "returncode": None, "stage": "compile"}

    server = None
    readers = []
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    state = {"total": 0, "limit": False}
    lock = threading.Lock()
    ready = threading.Event()

    with tempfile.TemporaryDirectory(prefix="minipar-web-teste1-") as temp:
        work = Path(temp)
        client_file = work / "teste01_cliente.mp"
        server_file = work / "teste01_servidor.mp"
        client_file.write_text(client_source, encoding="utf-8")
        server_file.write_text(server_source, encoding="utf-8")
        build_dir = work / "build"
        try:
            server_build = build_executable(str(server_file), out_dir=str(build_dir),
                                            timeout=COMPILE_TIMEOUT_SECONDS)
            client_build = build_executable(str(client_file), out_dir=str(build_dir),
                                            timeout=COMPILE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "",
                    "stderr": f"Compilação do Teste 1 interrompida após {COMPILE_TIMEOUT_SECONDS} segundos.",
                    "returncode": None, "timeout": True, "stage": "compile"}
        except Exception as exc:
            return {"ok": False, "stdout": "", "stderr": str(exc),
                    "returncode": None, "stage": "compile"}

        def drain(pipe, key):
            tail = b""
            try:
                while True:
                    chunk = pipe.read(_OUTPUT_CHUNK_BYTES)
                    if not chunk:
                        break
                    if key == "stderr" and b"aguardando conex" in (tail + chunk):
                        ready.set()
                    tail = (tail + chunk)[-64:]
                    with lock:
                        remaining = MAX_OUTPUT_BYTES - state["total"]
                        if remaining > 0:
                            kept = chunk[:remaining]
                            captured[key].extend(kept)
                            state["total"] += len(kept)
                        if len(chunk) > max(remaining, 0):
                            state["limit"] = True
                    if state["limit"] and server is not None:
                        _stop_process_tree(server)
            finally:
                pipe.close()

        try:
            server = subprocess.Popen(
                [str(server_build.exe_path.resolve()), "--node", "computador_2"],
                cwd=work, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
                start_new_session=(os.name == "posix"),
            )
            readers = [
                threading.Thread(target=drain, args=(server.stdout, "stdout"), daemon=True),
                threading.Thread(target=drain, args=(server.stderr, "stderr"), daemon=True),
            ]
            for reader in readers:
                reader.start()

            # O servidor abre o socket ao chegar ao primeiro receive().
            ready.wait(timeout=2)
            if server.poll() is not None:
                for reader in readers:
                    reader.join()
                server_out = bytes(captured["stdout"]).decode("utf-8", errors="replace")
                server_err = bytes(captured["stderr"]).decode("utf-8", errors="replace")
                return {"ok": False, "stdout": "=== Servidor ===\n" + server_out,
                        "stderr": server_err or "O servidor encerrou antes de aceitar o cliente.",
                        "returncode": server.returncode, "stage": "server"}

            client_result = _run_bounded_process(
                [str(client_build.exe_path.resolve()), "--node", "computador_1"],
                work, timeout, stdin_text=stdin_text,
            )

            server_stopped = True
            if client_result.get("timeout"):
                _stop_process_tree(server)
            else:
                try:
                    server.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    server_stopped = False
                    _stop_process_tree(server)
            if server.poll() is None:
                server.wait()
        except Exception as exc:
            if server is not None and server.poll() is None:
                _stop_process_tree(server)
                server.wait()
            return {"ok": False, "stdout": "", "stderr": str(exc),
                    "returncode": None, "stage": "run"}
        finally:
            for reader in readers:
                reader.join(timeout=2)

        server_out = bytes(captured["stdout"]).decode("utf-8", errors="replace")
        server_err = bytes(captured["stderr"]).decode("utf-8", errors="replace")
        client_out = client_result.get("stdout", "")
        client_err = client_result.get("stderr", "")
        stdout = "=== Servidor ===\n" + (server_out or "(sem saída)") + \
                 "\n=== Cliente ===\n" + (client_out or "(sem saída)")
        stderr_parts = [part for part in (server_err, client_err) if part]
        if not server_stopped:
            stderr_parts.append("O servidor não encerrou após a execução do cliente.")
        if state["limit"]:
            stderr_parts.append(f"Saída total interrompida no limite de {MAX_OUTPUT_BYTES // 1024} KiB.")
        server_ok = server.returncode == 0
        ok = client_result.get("ok", False) and server_ok and server_stopped and not state["limit"]
        return {
            "ok": ok, "stdout": stdout, "stderr": "\n".join(stderr_parts),
            "returncode": client_result.get("returncode"),
            "server_returncode": server.returncode,
            "timeout": client_result.get("timeout", False),
            "output_limit": state["limit"],
        }

class MiniParHandler(BaseHTTPRequestHandler):
    def _is_local_request(self):
        """Aceita apenas chamadas same-origin feitas pelo host local."""
        host_header = self.headers.get("Host", "")
        hostname = urlparse("//" + host_header).hostname
        if not hostname:
            return False
        try:
            is_loopback = ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            is_loopback = hostname.lower() == "localhost"
        if not is_loopback:
            return False

        origin = self.headers.get("Origin")
        if not origin:
            return False
        parsed_origin = urlparse(origin)
        if parsed_origin.scheme != "http" or parsed_origin.netloc.lower() != host_header.lower():
            return False

        fetch_site = self.headers.get("Sec-Fetch-Site", "").lower()
        return fetch_site in ("", "same-origin", "none")
    server_version = "MiniParWeb/1.0"
    def _json(self, data: dict, status: int = 200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)
    def _file(self, path: Path, content_type: str):
        if not path.is_file():
            self.send_error(404); return
        payload = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)
    def do_GET(self):
        path = urlparse(self.path).path
        static = {"/": ("index.html", "text/html; charset=utf-8"),
                  "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                  "/style.css": ("style.css", "text/css; charset=utf-8")}
        if path in static:
            name, kind = static[path]; return self._file(WEB_DIR / name, kind)
        if path == "/api/examples":
            return self._json({"examples": [p.name for p in sorted(EXAMPLES_DIR.glob("*.mp")) if is_web_example(p.name)]})
        if path.startswith("/api/examples/"):
            name = unquote(path.removeprefix("/api/examples/"))
            candidate = (EXAMPLES_DIR / name).resolve()
            if candidate.parent != EXAMPLES_DIR.resolve() or candidate.suffix != ".mp":
                return self._json({"error": "Exemplo inválido."}, 400)
            if not is_web_example(name):
                return self._json({"error": "Exemplo não disponível na interface Web."}, 404)
            if not candidate.is_file():
                return self._json({"error": "Exemplo não encontrado."}, 404)
            return self._json({"source": candidate.read_text(encoding="utf-8")})
        self.send_error(404)
    def do_POST(self):
        if not self._is_local_request():
            return self._json({"error": "Requisição cross-origin bloqueada."}, 403)
        path = urlparse(self.path).path
        if path not in ("/api/analyze", "/api/run", "/api/run-test1", "/api/run-fork-remote"):
            return self._json({"error": "Rota não encontrada."}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._json({"error": "Cabeçalho Content-Length inválido."}, 400)
        if length <= 0:
            return self._json({"error": "O corpo da requisição está vazio."}, 400)
        if length > MAX_REQUEST_BYTES:
            return self._json({"error": "Requisição muito grande. Limite de código: 128 KiB; entrada: 64 KiB."}, 413)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("O corpo da requisição deve ser um objeto JSON.")
            source = payload.get("source", "")
            stdin_text = payload.get("stdin", "")
            if not isinstance(source, str):
                raise ValueError("O campo 'source' deve ser texto.")
            if not isinstance(stdin_text, str):
                raise ValueError("O campo 'stdin' deve ser texto.")
            if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
                return self._json({"error": "Envie código com até 128 KiB."}, 413)
            if len(stdin_text.encode("utf-8")) > MAX_STDIN_BYTES:
                return self._json({"error": "A entrada do programa deve ter até 64 KiB."}, 413)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return self._json({"error": str(exc)}, 400)
        if path == "/api/analyze":
            try: return self._json(analyze_source(source))
            except Exception as exc: return self._json({"ok": False, "error": str(exc)}, 500)
        is_test1 = path == "/api/run-test1"
        is_fork_remote = path == "/api/run-fork-remote"
        if is_test1:
            example = payload.get("example", "")
            if not isinstance(example, str) or example not in TEST1_EXAMPLES:
                return self._json({"error": "Selecione um dos programas do Teste 1."}, 400)
            if not _TEST1_SLOT.acquire(blocking=False):
                return self._json({"ok": False, "error": "O Teste 1 já está em execução. Aguarde terminar."}, 429)
        if not _RUN_SLOTS.acquire(blocking=False):
            if is_test1:
                _TEST1_SLOT.release()
            return self._json({"ok": False, "error": "Limite de execuções simultâneas atingido. Tente novamente."}, 429)
        try:
            if is_test1:
                return self._json(run_test1(source, example, stdin_text=stdin_text))
            if is_fork_remote:
                return self._json(run_fork_remote(source))
            return self._json(run_source(source, stdin_text=stdin_text))
        finally:
            _RUN_SLOTS.release()
            if is_test1:
                _TEST1_SLOT.release()

def main(argv=None):
    parser = argparse.ArgumentParser(description="Interface Web local do MiniPar 2026.2")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), MiniParHandler)
    print(f"MiniPar Web disponível em http://{args.host}:{args.port}")
    print("Use Ctrl+C para encerrar.")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
