CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -g

TARGET = shell

SRC = \
	main.c \
	prompt.c \
	parser.c \
	scanner.c \
	source.c \
	node.c \
	executor.c \
	initsh.c \
	symtab/symtab.c \
	builtins/builtins.c \
	builtins/dump.c \
	builtins/delphi.c \
	delphi_mode.c \
	delphi_bridge.c

PYTHON = .venv/bin/python
PIP = .venv/bin/pip

# Windows fallback
ifeq ($(OS),Windows_NT)
	PYTHON = .venv/Scripts/python.exe
	PIP = .venv/Scripts/pip.exe
endif

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)

venv:
	python3 -m venv .venv || python -m venv .venv

deps: venv requirements.txt
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

dataset: deps
	$(PYTHON) delphi/build_dataset.py

train: dataset
	$(PYTHON) delphi/train_delphi.py

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET) *.o
	rm -rf __pycache__

distclean: clean
	rm -rf .venv
	rm -rf delphi/model

rebuild: clean all

.PHONY: all venv deps dataset train run clean distclean rebuild