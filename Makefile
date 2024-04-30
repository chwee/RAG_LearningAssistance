.ONESHELL:

VENV := venv
BIN := $(VENV)/bin/
SYS_PY := $(or $(shell which python3), $(shell which py))
PYTHON = $(BIN)python
ANY_PY = $(or $(wildcard $(PYTHON)), $(SYS_PY))


# =================================== DEFAULT =================================== #

default: all

## Default: default: Install dependencies
.PHONY: default
all: install

# =================================== HELPERS =================================== #

## Misc: help: print this help message
.PHONY: help
help:
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Commands:'
	@sed -n 's/^## Default: //p' ${MAKEFILE_LIST} | column -t -s ':' |  sed -e 's/^/ /'
	@echo ''
	@echo 'Misc:'
	@sed -n 's/^## Misc: //p' ${MAKEFILE_LIST} | column -t -s ':' |  sed -e 's/^/ /'
	@echo ''
	@echo 'Extra:'
	@sed -n 's/^## Extra: //p' ${MAKEFILE_LIST} | column -t -s ':' |  sed -e 's/^/ /'

## Default: venv: Create a python venv if it does not exist
.PHONY: venv
venv:
	test -d venv || '$(SYS_PY)' -m venv venv

## Default: install: Install dependencies
.PHONY: install
install: install/node install/python

## Extra: install/python: Install python dependencies
.PHONY: install/python
install/python: venv
	$(BIN)pip install -r requirements.txt
	$(BIN)pip install -r requirements-dev.txt

## Extra: install/node: Install node dependencies
.PHONY: install/node
install/node:
	npm i

# =================================== DEVELOPMENT =================================== #

## Default: build: Builds client
.PHONY: build
build: fmt test
	npm run build

## Default: dev: Run development server
.PHONY: dev
dev: install
	npx concurrently -n "client,server" -c blue,green --kill-others "npm:dev" "$(BIN)hupper -m waitress --port=8080 run:app"

## Default: start: Run production server
.PHONY: server
server: install build
	npx concurrently -n "client,server" -c blue,green --kill-others "npm:start" "$(BIN)waitress --port=8080 run:app"

## Default: test: Test the program
.PHONY: test
test: test/client test/server

## Extra: test/client: Run client tests
.PHONY: test/client
test/client: install/node
	npm run test

## Extra: test/server: Run server tests
.PHONY: test/server
test/server: install/python
	$(BIN)pytest -xsv

# =================================== QUALITY ================================== #

## Misc: clean: Remove cache files and build artifacts
.PHONY: clean
clean:
	$(ANY_PY) - <<-EOF
		pathlib = __import__("pathlib")
		def rm_rf(path): dir = pathlib.Path(path); return dir.unlink() if dir.is_file() else ([
			rm_rf(p) if p.is_dir() else p.unlink()
			for p in dir.iterdir()
		] and dir.rmdir())
		work_dir = pathlib.Path(".")
		for p in work_dir.rglob("*.py[co]"): rm_rf(p)
		for p in work_dir.rglob("__pycache__"): rm_rf(p)
		for p in work_dir.rglob(".pytest_cache"): rm_rf(p)
		rm_rf("client/dist")
	EOF

## Misc: fmt: Formats code
.PHONY: fmt
fmt:
	npm run lint:fix
	npx prettier --write --cache .
	$(BIN)ruff format

## Misc: lint: Lint code
.PHONY: lint
lint:
	npm run lint
	npx prettier --check --cache .
	$(BIN)ruff check

