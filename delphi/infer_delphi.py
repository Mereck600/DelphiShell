import json
import re
import sys
from pathlib import Path

import torch
from transformers import GPT2LMHeadModel, GPT2TokenizerFast

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "model"


def build_recursive_subfolder_command(base_folder: str, subfolder_name: str) -> str:
    base = base_folder.strip().strip("\"'")
    child = subfolder_name.strip().strip("\"'")
    return f'find "{base}" -type d -exec mkdir -p "{{}}/{child}" \\;'


def build_recursive_copy_command(base_folder: str, filename: str) -> str:
    base = base_folder.strip().strip("\"'")
    file_name = filename.strip().strip("\"'")
    return f'find "{base}" -type d -exec cp "{file_name}" "{{}}/{file_name}" \\;'


def safe_fallback(user_text: str) -> dict:
    # Maps common requests to safe actions when no model is available
    # or when generation fails validation.
    print(f"Model dir is {MODEL_DIR}")
    print("Fallback is called...")
    text = user_text.lower().strip()

    if text in ["list files", "show files", "display files", "ls", "list directory"]:
        return {"mode": "shell", "command": "ls"}

    if text in [
        "show current directory",
        "current directory",
        "where am i",
        "pwd",
        "print working directory",
    ]:
        return {"mode": "shell", "command": "pwd"}

    if text.startswith("run ") and text.endswith(".py"):
        filename = text[4:].strip()
        return {"mode": "run_file", "command": f"python3 {filename}"}

    if text.startswith("run ") and text.endswith(".js"):
        filename = text[4:].strip()
        return {"mode": "run_file", "command": f"node {filename}"}

    if text.startswith("make directory "):
        dirname = text.replace("make directory ", "", 1).strip()
        if dirname:
            return {"mode": "shell", "command": f"mkdir -p {dirname}"}

    if text.startswith("create directory "):
        dirname = text.replace("create directory ", "", 1).strip()
        if dirname:
            return {"mode": "shell", "command": f"mkdir -p {dirname}"}

    if text.startswith("make a file called ") and text.endswith(".txt"):
        filename = text.replace("make a file called ", "", 1).strip()
        if filename:
            return {"mode": "write_file", "path": filename, "content": ""}

    recursive_subfolder_patterns = [
        r"move to (.+?) folder and go into all subfolders and create a subfolder (.+)",
        r"go into all subfolders in (.+?) and create a subfolder named (.+)",
        r"create a subfolder named (.+) inside every folder in (.+)",
        r"add a subfolder called (.+) to every subfolder in (.+)",
        r"visit every folder under (.+) and make a (.+) subfolder",
        r"for each folder in (.+), create the subfolder (.+)",
    ]
    for pattern in recursive_subfolder_patterns:
        match = re.fullmatch(pattern, text)
        if not match:
            continue

        if "inside every folder in" in pattern or "add a subfolder called" in pattern:
            child, base = match.groups()
        else:
            base, child = match.groups()

        return {
            "mode": "shell",
            "command": build_recursive_subfolder_command(base, child),
        }

    recursive_copy_patterns = [
        r"copy (.+) into every subfolder in (.+)",
        r"put (.+) inside each folder under (.+)",
        r"walk through (.+) and copy (.+) to every subfolder",
        r"add (.+) to all directories in (.+)",
    ]
    for pattern in recursive_copy_patterns:
        match = re.fullmatch(pattern, text)
        if not match:
            continue

        if pattern.startswith("walk through"):
            base, filename = match.groups()
        else:
            filename, base = match.groups()

        return {
            "mode": "shell",
            "command": build_recursive_copy_command(base, filename),
        }

    return {
        "mode": "answer",
        "text": "I could not confidently map that request."
    }


def extract_first_json_object(text: str):
    # Scans generated text and returns the first complete JSON object it finds.
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == "\\":
            escape = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        return None

    return None


def normalize_action(action: dict) -> dict:
    # Validates the model response and normalizes it into one supported action shape.
    if not isinstance(action, dict):
        return {
            "mode": "answer",
            "text": "Model output was not a valid action object."
        }

    mode = action.get("mode")
    if mode not in {"shell", "write_file", "run_file", "answer"}:
        return {
            "mode": "answer",
            "text": "Model returned an unsupported action mode."
        }

    if mode in {"shell", "run_file"}:
        command = action.get("command", "")
        if not isinstance(command, str) or not command.strip():
            return {
                "mode": "answer",
                "text": "Model returned an empty command."
            }
        return {"mode": mode, "command": command.strip()}

    if mode == "write_file":
        path = action.get("path", "")
        content = action.get("content", "")
        if not isinstance(path, str) or not path.strip():
            return {
                "mode": "answer",
                "text": "Model returned an invalid file path."
            }
        if not isinstance(content, str):
            content = str(content)
        return {
            "mode": "write_file",
            "path": path.strip(),
            "content": content
        }

    text = action.get("text", "")
    if not isinstance(text, str) or not text.strip():
        text = "I could not interpret that request."
    return {"mode": "answer", "text": text.strip()}


def generate_action(user_text: str) -> dict:
    # Loads the local model, generates a JSON action, and falls back safely if
    # the model is missing or returns something unusable.
    if not MODEL_DIR.exists():
        print("Can't find model dir calling safefallback...")
        return safe_fallback(user_text)

    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = GPT2TokenizerFast.from_pretrained(str(MODEL_DIR))
        model = GPT2LMHeadModel.from_pretrained(str(MODEL_DIR))
        model.eval()
        model.to(device)

        prompt = f"Instruction: {user_text}\nJSON: "
        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=72,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        action = extract_first_json_object(decoded)
        if action is None:
            print("Action is none calling fallback...")
            return safe_fallback(user_text)

        return normalize_action(action)
    except Exception as e:
        print(f"There was an exception calling fallback...{e}")
        return safe_fallback(user_text)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "mode": "answer",
            "text": "No input provided."
        }))
        return

    user_text = " ".join(sys.argv[1:]).strip()
    if not user_text:
        print(json.dumps({
            "mode": "answer",
            "text": "No input provided."
        }))
        return

    action = generate_action(user_text)
    print(json.dumps(action, separators=(",", ":")))


if __name__ == "__main__":
    main()
