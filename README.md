# DelphiShell
AI integrated shell for interacting with DelphiOS

to run 
```
gcc -o shell executor.c initsh.c main.c node.c parser.c prompt.c scanner.c source.c builtins/builtins.c builtins/dump.c symtab/symtab.c

```

Run with delphi 

python requirements
```bash
pip install torch transformers datasets
```
Note: this right now is for cpu only, I will be working on detecting gpu and using if available.

```bash
gcc -o shell \
  main.c prompt.c parser.c scanner.c source.c node.c executor.c initsh.c \
  delphi_mode.c delphi_bridge.c \
  symtab/symtab.c \
  builtins/builtins.c builtins/dump.c builtins/delphi.c
```
or simply run
```bash
make deps
make
make train
make run
```

Example delphi current output

```
{"mode":"shell","command":"ls -la"}
{"mode":"write_file","path":"hello.py","content":"print('hi')"}
{"mode":"run_file","command":"python3 hello.py"}
{"mode":"answer","text":"I could not safely interpret that request."}

```

Next Steps:
Practical limitations

A tiny transformer trained from scratch will not be smart at first.

So the best realistic path is:

Start with the tiny GPT-2 config above.
Train on tightly formatted command/action pairs.
Keep rule-based fallback logic in infer_delphi.py.
Only let the model map to a small set of allowed action types.
Add confirmations for dangerous actions like:
rm
overwriting files
recursive moves
package install

That will feel much more stable than giving the model unrestricted shell access.