import argparse
import json
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
JSON_PATH = DATA_DIR / "command_dataset.json"
JSONL_PATH = DATA_DIR / "commands.jsonl"
EVAL_PATH = DATA_DIR / "eval_dataset.json"

EXTERNAL_ALLOWED_PREFIXES = (
    "ls", "pwd", "touch", "mkdir", "cp", "mv", "cat", "head", "tail", "grep",
    "find", "stat", "whoami", "env", "printenv", "date", "echo", "git status",
    "git diff", "git log", "git branch", "python3 --version", "node --version",
    "npm --version", "gcc --version", "cargo --version", "python3 -m pytest",
    "npm test", "make test", "du", "ps", "free", "df", "uname", "hostname",
    "which", "type", "lsof", "vmstat", "w", "groups", "id", "locale", "lsblk",
)
EXTERNAL_FORBIDDEN_FRAGMENTS = ("&&", "||", ";", "|", ">", "<", "`", "$(")
EXTERNAL_FORBIDDEN_PREFIXES = (
    "rm", "rmdir", "unlink", "sudo", "apt", "apt-get", "apt-cache", "pip",
    "npm install", "chown", "chmod", "dd", "mkfs", "shutdown", "reboot",
    "kill", "pkill", "killall", "crontab", "ssh", "scp", "curl", "wget",
)


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


def recursive_copy_command(base_folder, filename):
    return f'find "{base_folder}" -type d -exec cp "{filename}" "{{}}/{filename}" \\;'


def plan_cd_then_shell(path, command):
    return {
        "mode": "plan",
        "steps": [
            {"mode": "cd", "path": path},
            {"mode": "shell", "command": command},
        ],
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build the Delphi training dataset")
    parser.add_argument(
        "--include-nl2sh-alfa",
        action="store_true",
        help="Mix in a filtered subset of westenfelder/NL2SH-ALFA shell examples.",
    )
    parser.add_argument(
        "--nl2sh-limit",
        type=int,
        default=3000,
        help="Maximum number of NL2SH-ALFA rows to import.",
    )
    return parser.parse_args(argv)


def normalize_shell_command(command):
    return " ".join(str(command).strip().split())


def is_supported_external_command(command):
    normalized = normalize_shell_command(command)
    if not normalized:
        return False

    if any(fragment in normalized for fragment in EXTERNAL_FORBIDDEN_FRAGMENTS):
        return False

    for prefix in EXTERNAL_FORBIDDEN_PREFIXES:
        if normalized == prefix or normalized.startswith(prefix + " "):
            return False

    for prefix in EXTERNAL_ALLOWED_PREFIXES:
        if normalized == prefix or normalized.startswith(prefix + " "):
            return True

    return False


def build_shell_alias_examples():
    examples = []
    shell_aliases = [
        ("ls", ["list files", "show files", "display files", "show directory contents"]),
        ("pwd", ["show current directory", "print working directory", "where am i", "what folder am i in"]),
        ("ls -la", ["list all files with details", "show hidden files with details", "display long directory listing"]),
        ("find . -maxdepth 2 -type f", ["find files within two levels", "show files up to depth two", "list files in current folder and subfolders to depth two"]),
        ("find . -type d", ["show all folders recursively", "list all directories under the current folder", "find every directory recursively"]),
        ("du -sh .", ["show folder size", "display current directory size", "check how big this directory is"]),
        ("git status", ["show git status", "check repository status", "what changed in git"]),
        ("git log --oneline -5", ["show the last five commits", "display recent git commits", "list five recent commits"]),
        ("git diff --stat", ["show git diff summary", "summarize changed files in git", "show changed file stats"]),
        ("git branch", ["list git branches", "show git branches", "what branches exist"]),
        ("git checkout main", ["switch to main branch", "checkout main branch", "move to the main branch"]),
        ("ps aux", ["show running processes", "list active processes", "display all processes"]),
        ("env", ["show environment variables", "print environment variables", "display environment variables"]),
        ("date", ["show the date", "print current date", "what time is it"]),
        ("whoami", ["show current user", "who am i", "print my username"]),
        ("python3 --version", ["show python version", "print python version", "check installed python version"]),
        ("node --version", ["show node version", "print node version", "check node version"]),
        ("npm --version", ["show npm version", "print npm version", "check npm version"]),
        ("gcc --version", ["show gcc version", "print gcc version", "check c compiler version"]),
        ("cargo --version", ["show cargo version", "print cargo version", "check cargo version"]),
        ("python3 -m pytest", ["run the python tests", "execute pytest", "run all tests with pytest"]),
        ("npm test", ["run npm tests", "execute javascript tests", "run the test script"]),
        ("make test", ["run make test", "execute the makefile tests", "start tests with make"]),
        ("python3 -m http.server 8000", ["start a local web server on port 8000", "serve the current directory on port 8000", "run a simple http server on 8000"]),
    ]
    for command, prompts in shell_aliases:
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "shell", "command": command})
    return examples


def build_directory_examples():
    examples = []
    roots = [
        "src", "tests", "docs", "scripts", "build", "dist", "assets", "logs", "tmp",
        "data", "config", "examples", "archive", "backups", "reports", "fixtures",
        "images", "styles", "components", "public", "services", "modules", "themes",
        "plugins", "clients", "workspace", "content", "releases", "packages", "tools",
        "bin", "lib", "configs", "jobs", "workers", "sites", "templates", "migrations",
    ]
    nested = [
        "src/components", "src/utils", "src/data", "src/hooks", "src/pages", "src/lib",
        "tests/unit", "tests/integration", "tests/fixtures", "docs/api", "docs/guides",
        "docs/examples", "logs/archive", "assets/images", "assets/styles", "assets/icons",
        "tmp/cache", "config/env", "public/uploads", "services/auth", "services/api",
        "packages/core", "packages/ui", "modules/shared", "themes/default", "clients/acme",
        "clients/umbrella", "sites/admin", "sites/landing", "workers/queue", "jobs/daily",
        "templates/email", "templates/pdf", "migrations/sql", "configs/local",
    ]
    dir_verbs = ["make", "create", "add", "generate", "set up", "build"]
    dir_nouns = ["directory", "folder"]
    dir_starters = ["named", "called"]

    for name in roots:
        for verb, noun, starter in product(dir_verbs, dir_nouns, dir_starters):
            add_example(examples, f"{verb} a {noun} {starter} {name}", {"mode": "shell", "command": f"mkdir -p {name}"})
        for prompt in [f"make {name} folder", f"create {name} directory", f"set up {name}", f"add the folder {name}"]:
            add_example(examples, prompt, {"mode": "shell", "command": f"mkdir -p {name}"})

    for name in nested:
        prompts = [
            f"create the directory {name}",
            f"make folder {name}",
            f"set up the folder {name}",
            f"add the directory {name}",
            f"build out {name}",
        ]
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "shell", "command": f"mkdir -p {name}"})
    return examples


def build_recursive_examples():
    examples = []
    recursive_folder_examples = [
        ("project", "archive"), ("src", "generated"), ("docs", "drafts"),
        ("assets", "thumbnails"), ("clients", "reports"), ("workspace", "backup"),
        ("photos", "edited"), ("tests", "fixtures"), ("content", "images"),
        ("releases", "notes"), ("modules", "generated"), ("themes", "partials"),
        ("packages", "dist"), ("services", "logs"), ("configs", "snapshots"),
        ("sites", "assets"), ("workers", "artifacts"), ("templates", "cache"),
        ("plugins", "generated"), ("jobs", "output"),
    ]
    for base, child in recursive_folder_examples:
        command = recursive_subfolder_command(base, child)
        prompts = [
            f"move to {base} folder and go into all subfolders and create a subfolder {child}",
            f"go into all subfolders in {base} and create a subfolder named {child}",
            f"create a subfolder named {child} inside every folder in {base}",
            f"add a subfolder called {child} to every subfolder in {base}",
            f"visit every folder under {base} and make a {child} subfolder",
            f"for each folder in {base}, create the subfolder {child}",
            f"walk every directory in {base} and add a {child} folder",
            f"create {child} in every subdirectory of {base}",
        ]
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "shell", "command": command})

    recursive_copy_examples = [
        ("templates", "README.md"), ("services", "config.json"), ("projects", "Dockerfile"),
        ("clients", "notes.txt"), ("modules", "index.js"), ("packages", "package.json"),
        ("themes", "style.css"), ("examples", "main.py"), ("workers", "worker.py"),
        ("sites", "index.html"),
    ]
    for base, filename in recursive_copy_examples:
        command = recursive_copy_command(base, filename)
        prompts = [
            f"copy {filename} into every subfolder in {base}",
            f"put {filename} inside each folder under {base}",
            f"walk through {base} and copy {filename} to every subfolder",
            f"add {filename} to all directories in {base}",
            f"place {filename} in every nested folder in {base}",
        ]
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "shell", "command": command})
    return examples


def build_batch_structure_examples():
    examples = []
    batch_roots = [
        "client-a", "client-b", "client-c", "service-a", "service-b", "service-c",
        "package-a", "package-b", "theme-a", "theme-b", "workspace-a", "workspace-b",
        "plugin-a", "plugin-b", "site-a", "site-b", "worker-a", "worker-b",
    ]
    batch_child_dirs = ["logs", "reports", "archive", "input", "output", "drafts", "build", "dist", "cache", "assets"]
    for root, child in product(batch_roots, batch_child_dirs):
        command = f'mkdir -p "{root}/{child}"'
        prompts = [
            f"inside {root} create a {child} folder",
            f"make the directory {child} under {root}",
            f"add {child} inside {root}",
            f"set up {root}/{child}",
            f"create {root}/{child}",
        ]
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "shell", "command": command})
    return examples


def build_file_examples():
    examples = []
    empty_files = [
        "notes.txt", "todo.txt", "README.md", "config.json", "main.py", "app.js",
        "index.html", "style.css", "script.sh", "Dockerfile", ".gitignore",
        "requirements.txt", "package.json", "index.js", "server.py", "data.csv",
        "cli.py", "worker.js", "settings.toml", "docker-compose.yml", "env.example",
        "LICENSE", "CHANGELOG.md", "Makefile", "tsconfig.json",
    ]
    for name in empty_files:
        for prompt in [f"create a file named {name}", f"make an empty file called {name}", f"add a blank file named {name}", f"create {name}"]:
            add_example(examples, prompt, {"mode": "write_file", "path": name, "content": ""})

    file_templates = [
        ("hello.py", "print('hello world')\n", ["make hello.py that prints hello world", "create hello.py with a hello world print", "write a python hello world file named hello.py"]),
        ("main.py", "def main():\n    print('hi')\n\n\nif __name__ == '__main__':\n    main()\n", ["create main.py that prints hi", "make a python entry file named main.py that prints hi", "write main.py with a main function that prints hi"]),
        ("app.js", "console.log('hello from node');\n", ["create app.js that logs hello from node", "make app.js printing hello from node", "write a javascript file app.js that logs a greeting"]),
        ("index.html", "<!doctype html>\n<html>\n<head><title>Home</title></head>\n<body><h1>Hello</h1></body>\n</html>\n", ["create index.html with a hello heading", "make a basic html page called index.html", "write index.html with a simple hello page"]),
        ("style.css", "body {\n    font-family: sans-serif;\n    margin: 0;\n}\n", ["create style.css with a basic body rule", "make a stylesheet named style.css", "write style.css with simple body styles"]),
        ("script.sh", "#!/bin/sh\necho \"hello\"\n", ["create script.sh that echoes hello", "make a shell script named script.sh that prints hello", "write script.sh with a hello echo"]),
        ("README.md", "# Project\n\nA small starter project.\n", ["create a readme file", "make README.md for a small starter project", "write README.md with a short project heading"]),
        ("config.json", "{\n  \"debug\": true,\n  \"port\": 3000\n}\n", ["create config.json with debug enabled and port 3000", "make a config file with debug true", "write config.json for port 3000"]),
        ("docker-compose.yml", "services:\n  app:\n    image: nginx:latest\n    ports:\n      - \"8080:80\"\n", ["create a docker compose file for nginx", "make docker-compose.yml exposing port 8080", "write docker-compose.yml for a simple nginx service"]),
        (".gitignore", "__pycache__/\nnode_modules/\n.env\n", ["create a gitignore file", "make .gitignore for python and node", "write .gitignore with common ignores"]),
    ]
    for path, content, prompts in file_templates:
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "write_file", "path": path, "content": content})
    return examples


def build_run_examples():
    examples = []
    python_runs = ["main.py", "hello.py", "app.py", "server.py", "manage.py", "tool.py", "worker.py", "cli.py", "build.py", "seed.py", "migrate.py", "deploy.py"]
    for filename in python_runs:
        for prompt in [f"run {filename}", f"execute {filename}", f"start the python file {filename}", f"launch {filename}"]:
            add_example(examples, prompt, {"mode": "run_file", "command": f"python3 {filename}"})

    js_runs = ["app.js", "server.js", "index.js", "cli.js", "worker.js", "build.js", "seed.js", "watch.js", "deploy.js", "bundle.js"]
    for filename in js_runs:
        for prompt in [f"run {filename}", f"execute {filename} with node", f"launch {filename} using node", f"start {filename} with node"]:
            add_example(examples, prompt, {"mode": "run_file", "command": f"node {filename}"})
    return examples


def build_move_examples():
    examples = []
    filenames = ["test.py", "main.py", "README.md", "notes.txt", "config.json"]
    destinations = ["test", "tests", "src", "docs", "workspace", "archive"]

    for filename, dest in product(filenames, destinations):
        command = f'mv "{filename}" "{dest}/"'
        prompts = [
            f"move {filename} into {dest} directory",
            f"move {filename} into the {dest} directory",
            f"put {filename} in {dest}",
            f"place {filename} inside the {dest} folder",
        ]
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "shell", "command": command})

    return examples


def build_compile_examples():
    examples = []
    compile_examples = [
        ("main.c", "main"), ("program.c", "program"), ("tool.c", "tool"), ("app.c", "app"),
        ("server.c", "server"), ("client.c", "client"), ("worker.c", "worker"), ("shell.c", "shell"),
        ("daemon.c", "daemon"), ("parser.c", "parser"),
    ]
    for source, target in compile_examples:
        prompts = [
            f"compile {source}",
            f"use gcc to compile {source}",
            f"build {source}",
            f"compile {source} into an executable",
        ]
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "shell", "command": f"gcc -o {target} {source}"})
    return examples


def build_parametric_examples():
    examples = []
    projects = ["api", "frontend", "worker", "dashboard", "admin", "landing", "cli", "auth", "billing", "search", "catalog", "portal"]
    resources = ["logs", "reports", "archive", "input", "output", "cache", "images", "drafts", "exports", "imports", "fixtures", "temp"]
    verbs = ["create", "make", "set up", "add", "build"]
    for project_name, resource_name, verb in product(projects, resources, verbs):
        add_example(examples, f"{verb} the folder {project_name}/{resource_name}", {"mode": "shell", "command": f"mkdir -p {project_name}/{resource_name}"})
        add_example(examples, f"{verb} a {resource_name} directory in {project_name}", {"mode": "shell", "command": f"mkdir -p {project_name}/{resource_name}"})
        add_example(examples, f"{verb} {resource_name} under {project_name}", {"mode": "shell", "command": f"mkdir -p {project_name}/{resource_name}"})

    filenames = ["README.md", "config.json", "index.js", "main.py", "Dockerfile", "package.json", "requirements.txt", "notes.txt"]
    for project_name, filename in product(projects, filenames):
        add_example(examples, f"create {filename} inside {project_name}", {"mode": "write_file", "path": f"{project_name}/{filename}", "content": ""})
        add_example(examples, f"add an empty {filename} file to {project_name}", {"mode": "write_file", "path": f"{project_name}/{filename}", "content": ""})
        add_example(examples, f"make {project_name}/{filename}", {"mode": "write_file", "path": f"{project_name}/{filename}", "content": ""})
    return examples


def build_multi_step_examples():
    examples = []
    bases = ["project", "workspace", "client-a", "client-b", "service-a", "service-b", "package-a", "theme-a"]
    mids = ["src", "docs", "assets", "tests", "configs", "scripts"]
    leaves = ["generated", "drafts", "images", "fixtures", "logs", "output"]
    for base, mid, leaf in product(bases, mids, leaves):
        command = f'mkdir -p "{base}/{mid}/{leaf}"'
        prompts = [
            f"inside {base}, create {mid}/{leaf}",
            f"make the folder {base}/{mid}/{leaf}",
            f"set up {leaf} under {base}/{mid}",
            f"create the nested directory {base}/{mid}/{leaf}",
        ]
        for prompt in prompts:
            add_example(examples, prompt, {"mode": "shell", "command": command})
    return examples


def build_plan_examples():
    examples = []
    bases = [
        "test", "test1", "project", "workspace", "src", "docs",
        "assets", "tests", "client-a", "service-a", "package-a", "theme-a",
    ]
    child_dirs = [
        "test5", "archive", "drafts", "generated", "fixtures",
        "logs", "output", "images", "reports", "cache",
    ]

    for base, child in product(bases, child_dirs):
        action = plan_cd_then_shell(base, f'mkdir -p "{child}"')
        prompts = [
            f"move into the {base} directory and add a subdirectory called {child}",
            f"move into the {base} directory and create a subdirectory called {child}",
            f"go into the {base} directory and add a subdirectory called {child}",
            f"go into the {base} directory and create a subdirectory called {child}",
            f"change directory to the {base} directory and add a subdirectory called {child}",
            f"change directory to the {base} directory and create a subdirectory called {child}",
            f"enter the {base} folder and create a directory named {child}",
            f"switch to {base} and make a folder called {child}",
        ]
        for prompt in prompts:
            add_example(examples, prompt, action)

    files = ["README.md", "notes.txt", "config.json", "main.py"]
    for base, filename in product(bases, files):
        action = plan_cd_then_shell(base, f'touch "{filename}"')
        prompts = [
            f"move into the {base} directory and create a file named {filename}",
            f"go into the {base} directory and make a file called {filename}",
            f"change directory to {base} and create {filename}",
            f"enter the {base} folder and add an empty file named {filename}",
        ]
        for prompt in prompts:
            add_example(examples, prompt, action)

    run_targets = [("main.py", "python3 main.py"), ("worker.py", "python3 worker.py"), ("app.js", "node app.js")]
    for base, (target, command) in product(bases, run_targets):
        action = plan_cd_then_shell(base, command)
        prompts = [
            f"move into the {base} directory and run {target}",
            f"go into the {base} directory and execute {target}",
            f"change directory to {base} and start {target}",
        ]
        for prompt in prompts:
            add_example(examples, prompt, action)

    return examples


def build_external_nl2sh_alfa_examples(limit):
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets library not available, skipping NL2SH-ALFA import")
        return []

    rows = load_dataset("westenfelder/NL2SH-ALFA", "train", split="train")
    examples = []

    for row in rows:
        if row.get("difficulty", 0) > 1:
            continue

        instruction = str(row.get("nl", "")).strip()
        command = normalize_shell_command(row.get("bash", ""))
        if not instruction or not is_supported_external_command(command):
            continue

        add_example(examples, instruction, {"mode": "shell", "command": command})
        if len(examples) >= limit:
            break

    print(f"Imported {len(examples)} filtered NL2SH-ALFA examples")
    return examples


def build_answer_examples():
    examples = []
    answers = [
        ("tell me a joke", "I can help with shell-style actions, file creation, and running files."),
        ("what is the meaning of life", "I can help map requests into shell commands or simple file actions."),
        ("who won the world series", "I am trained for local command actions and cannot answer that confidently."),
        ("write me a poem", "I am focused on command execution and simple project scaffolding tasks."),
        ("explain quantum mechanics", "I can help with terminal tasks, but I cannot answer that confidently here."),
        ("browse the web for me", "I am focused on local shell and file actions in this project."),
        ("solve calculus for me", "I am focused on mapping local instructions to shell and file actions."),
        ("tell me the weather", "I can help with local shell and file actions but not live weather."),
        ("summarize this novel", "I am focused on terminal and project actions in this environment."),
        ("who is the president", "I am trained for local command execution tasks, not current events."),
    ]
    for prompt, text in answers:
        add_example(examples, prompt, {"mode": "answer", "text": text})
        add_example(examples, f"please {prompt}", {"mode": "answer", "text": text})
    return examples


def dedupe_and_sort(examples):
    deduped = []
    seen = set()
    for row in examples:
        key = (row["instruction"], json.dumps(row["action"], sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    deduped.sort(key=lambda row: row["instruction"])
    return deduped


def build_eval_examples():
    examples = []
    eval_rows = [
        ("show the last five commits", {"mode": "shell", "command": "git log --oneline -5"}),
        ("show git status", {"mode": "shell", "command": "git status"}),
        ("move to project folder and go into all subfolders and create a subfolder archive", {"mode": "shell", "command": recursive_subfolder_command("project", "archive")}),
        ("copy Dockerfile into every subfolder in projects", {"mode": "shell", "command": recursive_copy_command("projects", "Dockerfile")}),
        ("create the nested directory workspace/docs/drafts", {"mode": "shell", "command": 'mkdir -p "workspace/docs/drafts"'}),
        ("move into the test directory and add a subdirectory called test5", plan_cd_then_shell("test", 'mkdir -p "test5"')),
        ("go into the workspace directory and make a file called README.md", plan_cd_then_shell("workspace", 'touch "README.md"')),
        ("change directory to service-a and start worker.py", plan_cd_then_shell("service-a", "python3 worker.py")),
        ("run worker.py", {"mode": "run_file", "command": "python3 worker.py"}),
        ("execute bundle.js with node", {"mode": "run_file", "command": "node bundle.js"}),
        ("create config.json inside billing", {"mode": "write_file", "path": "billing/config.json", "content": ""}),
        ("make an empty file called LICENSE", {"mode": "write_file", "path": "LICENSE", "content": ""}),
        ("tell me the weather", {"mode": "answer", "text": "I can help with local shell and file actions but not live weather."}),
    ]
    for instruction, action in eval_rows:
        add_example(examples, instruction, action)
    return examples


def build_examples(include_nl2sh_alfa=False, nl2sh_limit=3000):
    examples = []
    for builder in [
        build_shell_alias_examples,
        build_directory_examples,
        build_recursive_examples,
        build_batch_structure_examples,
        build_file_examples,
        build_run_examples,
        build_move_examples,
        build_compile_examples,
        build_parametric_examples,
        build_multi_step_examples,
        build_plan_examples,
        build_answer_examples,
    ]:
        examples.extend(builder())

    if include_nl2sh_alfa:
        examples.extend(build_external_nl2sh_alfa_examples(nl2sh_limit))

    return dedupe_and_sort(examples)


def write_outputs(examples, eval_examples):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "format": "delphi-command-dataset-v4",
        "count": len(examples),
        "records": examples,
    }

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for row in examples:
            f.write(json.dumps({"text": row["text"]}) + "\n")

    with open(EVAL_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "format": "delphi-eval-dataset-v1",
                "count": len(eval_examples),
                "records": eval_examples,
            },
            f,
            indent=2,
        )


def main(argv=None):
    args = parse_args(argv)
    examples = build_examples(
        include_nl2sh_alfa=args.include_nl2sh_alfa,
        nl2sh_limit=args.nl2sh_limit,
    )
    eval_examples = build_eval_examples()
    write_outputs(examples, eval_examples)
    print(f"Wrote {len(examples)} examples to {JSON_PATH}")
    print(f"Wrote training rows to {JSONL_PATH}")
    print(f"Wrote {len(eval_examples)} eval examples to {EVAL_PATH}")


if __name__ == "__main__":
    main()
