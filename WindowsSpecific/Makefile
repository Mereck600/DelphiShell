#windows specific makefile
CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -g

TARGET = shell.exe

SRC = \
	main.c \
	prompt.c \
	parser.c \
	scanner.c \
	source.c \
	node.c \
	executor.c \
	initsh.c \
	symtab.c \
	builtins.c \
	dump.c \
	delphi_mode.c \
	delphi_bridge.c

PYTHON = .venv/Scripts/python.exe
PIP = .venv/Scripts/pip.exe

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)

venv:
	python -m venv .venv

deps: venv requirements.txt
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

dataset: deps
	$(PYTHON) delphi/build_dataset.py

train: dataset
	$(PYTHON) delphi/train_delphi.py

run: $(TARGET)
	$(TARGET)

clean:
	del /Q $(TARGET) 2>nul || exit 0

distclean: clean
	rmdir /S /Q .venv 2>nul || exit 0
	rmdir /S /Q delphi\model 2>nul || exit 0

rebuild: clean all

.PHONY: all venv deps dataset train run clean distclean rebuild