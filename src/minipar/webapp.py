"""Interface Web didática local do MiniPar 2026.2."""
from __future__ import annotations
import argparse, json, subprocess, tempfile
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
MAX_SOURCE_BYTES = 128 * 1024

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

def run_source(source: str, timeout: int = 10) -> dict:
    """Compila e executa em pasta temporária, limitando o tempo de execução."""
    with tempfile.TemporaryDirectory(prefix="minipar-web-") as temp:
        work = Path(temp)
        path = work / "programa.mp"
        path.write_text(source, encoding="utf-8")
        try:
            build = build_executable(str(path), out_dir=str(work / "build"))
            proc = subprocess.run([str(build.exe_path.resolve())], cwd=work,
                                  capture_output=True, text=True, timeout=timeout, check=False)
            return {"ok": proc.returncode == 0, "stdout": proc.stdout,
                    "stderr": proc.stderr, "returncode": proc.returncode}
        except subprocess.TimeoutExpired as exc:
            # TimeoutExpired pode carregar stdout como bytes mesmo com text=True.
            partial_stdout = exc.stdout or ""
            if isinstance(partial_stdout, bytes):
                partial_stdout = partial_stdout.decode("utf-8", errors="replace")
            return {"ok": False, "stdout": partial_stdout,
                    "stderr": f"Execução interrompida após {timeout} segundos.",
                    "returncode": None, "timeout": True}
        except Exception as exc:
            return {"ok": False, "stdout": "", "stderr": str(exc), "returncode": None}

class MiniParHandler(BaseHTTPRequestHandler):
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
            return self._json({"examples": [p.name for p in sorted(EXAMPLES_DIR.glob("*.mp"))]})
        if path.startswith("/api/examples/"):
            name = unquote(path.removeprefix("/api/examples/"))
            candidate = (EXAMPLES_DIR / name).resolve()
            if candidate.parent != EXAMPLES_DIR.resolve() or candidate.suffix != ".mp":
                return self._json({"error": "Exemplo inválido."}, 400)
            if not candidate.is_file():
                return self._json({"error": "Exemplo não encontrado."}, 404)
            return self._json({"source": candidate.read_text(encoding="utf-8")})
        self.send_error(404)
    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/analyze", "/api/run"):
            return self._json({"error": "Rota não encontrada."}, 404)
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_SOURCE_BYTES:
            return self._json({"error": "Envie código com até 128 KiB."}, 413)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            source = payload.get("source", "")
            if not isinstance(source, str):
                raise ValueError("O campo 'source' deve ser texto.")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return self._json({"error": str(exc)}, 400)
        if path == "/api/analyze":
            try: return self._json(analyze_source(source))
            except Exception as exc: return self._json({"ok": False, "error": str(exc)}, 500)
        return self._json(run_source(source))

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
