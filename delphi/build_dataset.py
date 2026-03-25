import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "commands.jsonl"

examples = [
    ("list files", {"mode":"shell","command":"ls"}),
    ("show current directory", {"mode":"shell","command":"pwd"}),
    ("make directory src", {"mode":"shell","command":"mkdir -p src"}),
    ("create a file named notes.txt", {"mode":"write_file","path":"notes.txt","content":""}),
    ("make hello.py that prints hi", {"mode":"write_file","path":"hello.py","content":"print('hi')"}),
    ("run hello.py", {"mode":"run_file","command":"python3 hello.py"}),
    ("compile main.c", {"mode":"shell","command":"gcc -o main main.c"}),
]

OUT.parent.mkdir(parents=True, exist_ok=True)

with open(OUT, "w", encoding="utf-8") as f:
    for user, action in examples:
        row = {"text": f"User: {user}\nAction: {json.dumps(action, separators=(',', ':'))}"}
        f.write(json.dumps(row) + "\n")