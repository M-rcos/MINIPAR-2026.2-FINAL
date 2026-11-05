# Atalhos de desenvolvimento (Arch Linux: sudo pacman -S make python)
PY ?= python3
export PYTHONPATH := src

.PHONY: web teste8 teste9 teste10 test test-rapido tokens ast check tac cpp build run teste1-servidor teste1-cliente teste1-demo clean

web:
	$(PY) -m minipar.webapp

test:
	$(PY) -m unittest discover -s tests -v

test-rapido:
	$(PY) -m unittest tests.test_lexer tests.test_parser tests.test_semantic tests.test_tac

tokens:
	$(PY) -m minipar tokens $(F)

ast:
	$(PY) -m minipar ast $(F)

check:
	$(PY) -m minipar check $(F) --symbols

tac:
	$(PY) -m minipar tac $(F)

cpp:
	$(PY) -m minipar cpp $(F)

build:
	$(PY) -m minipar build $(F)

run:
	$(PY) -m minipar run $(F)

teste8:
	$(PY) -m minipar run exemplos/teste08_avaliacao_4nucleos.mp -O2
teste9:
	$(PY) -m minipar run exemplos/teste09_5nucleos_fractal.mp -O2
teste10:
	$(PY) -m minipar run exemplos/teste10_6nucleos_2fractais.mp -O2

teste1-servidor:
	$(PY) -m minipar build exemplos/teste01_servidor.mp > /dev/null
	./build/teste01_servidor --node computador_2

teste1-cliente:
	$(PY) -m minipar build exemplos/teste01_cliente.mp > /dev/null
	./build/teste01_cliente --node computador_1

teste1-demo:
	$(PY) -m minipar build exemplos/teste01_servidor.mp > /dev/null
	$(PY) -m minipar build exemplos/teste01_cliente.mp > /dev/null
	./build/teste01_servidor --node computador_2 & \
	sleep 1; printf '+\n3\n4\n*\n6\n7\n/\n1\n0\nsair\n' | ./build/teste01_cliente --node computador_1; wait

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
