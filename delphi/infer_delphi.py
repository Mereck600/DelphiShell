import os
import sys
import json
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
from transformers import GPT2LMHeadModel, GPT2TokenizerFast

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "model"


def safe_fallback(user_text: str) -> dict:
    # Maps a few common requests to safe actions when no model is available
    # or when generation fails validation.
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
        return safe_fallback(user_text)

    try:
        tokenizer = GPT2TokenizerFast.from_pretrained(str(MODEL_DIR))
        model = GPT2LMHeadModel.from_pretrained(str(MODEL_DIR))
        model.eval()
        model.to(torch.device("cpu"))

        prompt = f"Instruction: {user_text}\nJSON: "

        inputs = tokenizer(prompt, return_tensors="pt")

        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=40,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        decoded = tokenizer.decode(output[0], skip_special_tokens=True)

        action = extract_first_json_object(decoded)
        if action is None:
            return safe_fallback(user_text)

        return normalize_action(action)

    except Exception:
        return safe_fallback(user_text)


def main():
    # Reads the user instruction from argv and prints the final action as JSON.
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
