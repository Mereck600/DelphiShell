import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
JSON_PATH = DATA_DIR / "command_dataset.json"
JSONL_PATH = DATA_DIR / "commands.jsonl"


def add_example(examples, instruction, action):
    examples.append(
        {
            "instruction": instruction,
            "action": action,
            "text": f"Instruction: {instruction}\nJSON: {json.dumps(action, separators=(',', ':'))}",
        }
    )


def recursive_subfolder_command(base_folder, subfolder_name):
    return f'find "{base_folder}" -type d -exec mkdir -p "{{}}/{subfolder_name}" \\;'


def build_examples():
    examples = []

    shell_aliases = [
        ("ls", ["list files", "show files", "display files", "show directory contents"]),
        ("pwd", [
            "show current directory",
            "print working directory",
            "where am i",
            "what folder am i in",
        ]),
        ("ls -la", [
            "list all files with details",
            "show hidden files with details",
            "display long directory listing",
        ]),
        ("find . -maxdepth 2 -type f", [
            "find files within two levels",
            "show files up to depth two",
            "list files in current folder and subfolders to depth two",
        ]),
        ("du -sh .", [
            "show folder size",
            "display current directory size",
            "check how big this directory is",
        ]),
        ("git status", [
            "show git status",
            "check repository status",
            "what changed in git",
        ]),
        ("git log --oneline -5", [
            "show the last five commits",
            "display recent git commits",
            "list five recent commits",
        ]),
        ("ps aux", [
            "show running processes",
            "list active processes",
            "display all processes",
        ]),
        ("env", [
            "show environment variables",
            "print environment variables",
            "display environment variables",
        ]),
        ("date", [
            "show the date",
            "print current date",
            "what time is it",
        ]),
        ("whoami", [
            "show current user",
            "who am i",
            "print my username",
        ]),
        ("python3 --version", [
            "show python version",
            "print python version",
            "check installed python version",
        ]),
        ("node --version", [
            "show node version",
            "print node version",
            "check node version",
        ]),
        ("npm --version", [
            "show npm version",
            "print npm version",
            "check npm version",
        ]),
        ("gcc --version", [
            "show gcc version",
            "print gcc version",
            "check c compiler version",
        ]),
        ("cargo --version", [
            "show cargo version",
            "print cargo version",
            "check cargo version",
        ]),
        ("python3 -m pytest", [
            "run the python tests",
            "execute pytest",
            "run all tests with pytest",
        ]),
        ("npm test", [
            "run npm tests",
            "execute javascript tests",
            "run the test script",
        ]),
        ("make test", [
            "run make test",
            "execute the makefile tests",
            "start tests with make",
        ]),
        ("python3 -m http.server 8000", [
            "start a local web server on port 8000",
            "serve the current directory on port 8000",
            "run a simple http server on 8000",
        ]),
    ]

    for command, prompts in shell_aliases:
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "shell", "command": command})

    directories = [
        "src",
        "tests",
        "docs",
        "scripts",
        "build",
        "dist",
        "assets",
        "logs",
        "tmp",
        "data",
        "config",
        "examples",
    ]
    dir_verbs = ["make", "create", "add", "generate"]
    dir_nouns = ["directory", "folder"]
    for name in directories:
        for verb in dir_verbs:
            for noun in dir_nouns:
                add_example(
                    examples,
                    f"{verb} a {noun} named {name}",
                    {"mode": "shell", "command": f"mkdir -p {name}"},
                )
                add_example(
                    examples,
                    f"{verb} {name} {noun}",
                    {"mode": "shell", "command": f"mkdir -p {name}"},
                )

    nested_directories = [
        "src/components",
        "src/utils",
        "src/data",
        "tests/unit",
        "tests/integration",
        "docs/api",
        "logs/archive",
        "assets/images",
        "assets/styles",
        "tmp/cache",
    ]
    for name in nested_directories:
        add_example(
            examples,
            f"create the directory {name}",
            {"mode": "shell", "command": f"mkdir -p {name}"},
        )
        add_example(
            examples,
            f"make folder {name}",
            {"mode": "shell", "command": f"mkdir -p {name}"},
        )

    recursive_folder_examples = [
        ("project", "archive"),
        ("src", "generated"),
        ("docs", "drafts"),
        ("assets", "thumbnails"),
        ("clients", "reports"),
        ("workspace", "backup"),
        ("photos", "edited"),
        ("tests", "fixtures"),
    ]
    for base, child in recursive_folder_examples:
        command = recursive_subfolder_command(base, child)
        prompts = [
            f"move to {base} folder and go into all subfolders and create a subfolder {child}",
            f"go into all subfolders in {base} and create a subfolder named {child}",
            f"create a subfolder named {child} inside every folder in {base}",
            f"add a subfolder called {child} to every subfolder in {base}",
        ]
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "shell", "command": command})

    empty_files = [
        "notes.txt",
        "todo.txt",
        "README.md",
        "config.json",
        "main.py",
        "app.js",
        "index.html",
        "style.css",
        "script.sh",
        "Dockerfile",
        ".gitignore",
        "requirements.txt",
    ]
    for name in empty_files:
        add_example(
            examples,
            f"create a file named {name}",
            {"mode": "write_file", "path": name, "content": ""},
        )
        add_example(
            examples,
            f"make an empty file called {name}",
            {"mode": "write_file", "path": name, "content": ""},
        )

    file_templates = [
        (
            "hello.py",
            "print('hello world')\n",
            [
                "make hello.py that prints hello world",
                "create hello.py with a hello world print",
                "write a python hello world file named hello.py",
            ],
        ),
        (
            "main.py",
            "def main():\n    print('hi')\n\n\nif __name__ == '__main__':\n    main()\n",
            [
                "create main.py that prints hi",
                "make a python entry file named main.py that prints hi",
                "write main.py with a main function that prints hi",
            ],
        ),
        (
            "app.js",
            "console.log('hello from node');\n",
            [
                "create app.js that logs hello from node",
                "make app.js printing hello from node",
                "write a javascript file app.js that logs a greeting",
            ],
        ),
        (
            "index.html",
            "<!doctype html>\n<html>\n<head><title>Home</title></head>\n<body><h1>Hello</h1></body>\n</html>\n",
            [
                "create index.html with a hello heading",
                "make a basic html page called index.html",
                "write index.html with a simple hello page",
            ],
        ),
        (
            "style.css",
            "body {\n    font-family: sans-serif;\n    margin: 0;\n}\n",
            [
                "create style.css with a basic body rule",
                "make a stylesheet named style.css",
                "write style.css with simple body styles",
            ],
        ),
        (
            "script.sh",
            "#!/bin/sh\necho \"hello\"\n",
            [
                "create script.sh that echoes hello",
                "make a shell script named script.sh that prints hello",
                "write script.sh with a hello echo",
            ],
        ),
        (
            "README.md",
            "# Project\n\nA small starter project.\n",
            [
                "create a readme file",
                "make README.md for a small starter project",
                "write README.md with a short project heading",
            ],
        ),
        (
            "config.json",
            "{\n  \"debug\": true,\n  \"port\": 3000\n}\n",
            [
                "create config.json with debug enabled and port 3000",
                "make a config file with debug true",
                "write config.json for port 3000",
            ],
        ),
    ]

    for path, content, prompts in file_templates:
        for prompt in prompts:
            add_example(
                examples,
                prompt,
                {"mode": "write_file", "path": path, "content": content},
            )

    python_runs = ["main.py", "hello.py", "app.py", "server.py", "manage.py", "tool.py"]
    for filename in python_runs:
        add_example(
            examples,
            f"run {filename}",
            {"mode": "run_file", "command": f"python3 {filename}"},
        )
        add_example(
            examples,
            f"execute {filename}",
            {"mode": "run_file", "command": f"python3 {filename}"},
        )
        add_example(
            examples,
            f"start the python file {filename}",
            {"mode": "run_file", "command": f"python3 {filename}"},
        )

    js_runs = ["app.js", "server.js", "index.js", "cli.js", "worker.js"]
    for filename in js_runs:
        add_example(
            examples,
            f"run {filename}",
            {"mode": "run_file", "command": f"node {filename}"},
        )
        add_example(
            examples,
            f"execute {filename} with node",
            {"mode": "run_file", "command": f"node {filename}"},
        )

    compile_examples = [
        ("main.c", "main", "compile main.c"),
        ("program.c", "program", "compile program.c"),
        ("tool.c", "tool", "build tool.c"),
        ("app.c", "app", "compile app.c into an executable"),
    ]
    for source, target, prompt in compile_examples:
        add_example(
            examples,
            prompt,
            {"mode": "shell", "command": f"gcc -o {target} {source}"},
        )
        add_example(
            examples,
            f"use gcc to compile {source}",
            {"mode": "shell", "command": f"gcc -o {target} {source}"},
        )

    answers = [
        (
            "tell me a joke",
            "I can help with shell-style actions, file creation, and running files.",
        ),
        (
            "what is the meaning of life",
            "I can help map requests into shell commands or simple file actions.",
        ),
        (
            "who won the world series",
            "I am trained for local command actions and cannot answer that confidently.",
        ),
        (
            "write me a poem",
            "I am focused on command execution and simple project scaffolding tasks.",
        ),
        (
            "explain quantum mechanics",
            "I can help with terminal tasks, but I cannot answer that confidently here.",
        ),
    ]
    for prompt, text in answers:
        add_example(examples, prompt, {"mode": "answer", "text": text})
        add_example(examples, f"please {prompt}", {"mode": "answer", "text": text})

    deduped = []
    seen = set()
    for row in examples:
        key = (row["instruction"], json.dumps(row["action"], sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    return deduped


def write_outputs(examples):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "format": "delphi-command-dataset-v1",
        "count": len(examples),
        "records": examples,
    }

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for row in examples:
            f.write(json.dumps({"text": row["text"]}) + "\n")


def main():
    examples = build_examples()
    write_outputs(examples)
    print(f"Wrote {len(examples)} examples to {JSON_PATH}")
    print(f"Wrote training rows to {JSONL_PATH}")


if __name__ == "__main__":
    main()
