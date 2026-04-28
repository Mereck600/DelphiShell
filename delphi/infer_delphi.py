import json
import re
import sys
from pathlib import Path
from typing import Optional

import torch
from transformers import GPT2LMHeadModel, GPT2TokenizerFast

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "model"
_TOKENIZER = None
_MODEL = None
_DEVICE = None


def build_single_step_plan(path: str, command: str) -> dict:
    return {
        "mode": "plan",
        "steps": [
            {"mode": "cd", "path": path},
            {"mode": "shell", "command": command},
        ],
    }


def plan_compound_request(user_text: str) -> dict | None:
    text = " ".join(user_text.strip().split())
    patterns = [
        r"move into (?:the )?(.+?) directory and add (?:a )?subdirectory called (.+)",
        r"move into (?:the )?(.+?) directory and create (?:a )?subdirectory called (.+)",
        r"go into (?:the )?(.+?) directory and add (?:a )?subdirectory called (.+)",
        r"go into (?:the )?(.+?) directory and create (?:a )?subdirectory called (.+)",
        r"change directory to (?:the )?(.+?) directory and add (?:a )?subdirectory called (.+)",
        r"change directory to (?:the )?(.+?) directory and create (?:a )?subdirectory called (.+)",
    ]

    for pattern in patterns:
        match = re.fullmatch(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        base, child = match.groups()
        return build_single_step_plan(base.strip(), f'mkdir -p "{child.strip()}"')

    return None


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
    if mode not in {"shell", "write_file", "run_file", "answer", "cd", "plan"}:
        return {
            "mode": "answer",
            "text": "Model returned an unsupported action mode."
        }

    if mode == "cd":
        path = action.get("path", "")
        if not isinstance(path, str) or not path.strip():
            return {
                "mode": "answer",
                "text": "Model returned an invalid directory path."
            }
        return {"mode": "cd", "path": path.strip()}

    if mode == "plan":
        steps = action.get("steps")
        if not isinstance(steps, list) or not steps:
            return {
                "mode": "answer",
                "text": "Model returned an empty execution plan."
            }

        normalized_steps = []
        for step in steps:
            normalized = normalize_action(step)
            if normalized.get("mode") == "answer" and "steps" not in normalized:
                return {
                    "mode": "answer",
                    "text": "Model returned an invalid plan step."
                }
            if normalized.get("mode") == "plan":
                return {
                    "mode": "answer",
                    "text": "Nested plans are not supported."
                }
            normalized_steps.append(normalized)

        return {"mode": "plan", "steps": normalized_steps}

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


def load_model_once() -> bool:
    global _TOKENIZER, _MODEL, _DEVICE

    if _TOKENIZER is not None and _MODEL is not None and _DEVICE is not None:
        return True

    if not MODEL_DIR.exists():
        return False

    _DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _TOKENIZER = GPT2TokenizerFast.from_pretrained(str(MODEL_DIR))
    _MODEL = GPT2LMHeadModel.from_pretrained(str(MODEL_DIR))
    _MODEL.config.pad_token_id = _TOKENIZER.eos_token_id # JUST ADDED THIS NEED TO TEST
    _MODEL.eval()
    _MODEL.to(_DEVICE)
    return True


# def generate_action(user_text: str) -> dict:
#     # Loads the local model, generates a JSON action, and falls back safely if
#     # the model is missing or returns something unusable.
#     planned = plan_compound_request(user_text)
#     if planned is not None:
#         return planned

#     try:
#         if not load_model_once():
#             return safe_fallback(user_text)

#         prompt = (
#             "Translate the instruction into JSON.\n"
#             "Use mode plan with a steps array when the request contains multiple actions.\n"
#             "Supported modes: shell, write_file, run_file, answer, cd, plan.\n"
#             f"Instruction: {user_text}\nJSON: "
#         )
#         inputs = _TOKENIZER(prompt, return_tensors="pt")
#         inputs = {key: value.to(_DEVICE) for key, value in inputs.items()}

#         with torch.no_grad():
#             # output = _MODEL.generate(
#             #     **inputs,
#             #     max_new_tokens=48,
#             #     do_sample=False,
#             #     pad_token_id=_TOKENIZER.eos_token_id,
#             #     eos_token_id=_TOKENIZER.eos_token_id,
#             # )
#             output = _MODEL.generate(
#                     **inputs,
#                     max_new_tokens=120,
#                     do_sample=True,
#                     temperature=0.3,
#                     top_p=0.9,
#             )

#         decoded = _TOKENIZER.decode(output[0], skip_special_tokens=True)
#         action = extract_first_json_object(decoded)
#         if action is None:
#             return safe_fallback(user_text)

#         return normalize_action(action)
#     except Exception as e:
#         print(f"Delphi inference error: {e}", file=sys.stderr)
#         return safe_fallback(user_text)
def generate_action(user_text: str) -> dict:
    """
    Loads the local Delphi model, generates a JSON action, validates it,
    and falls back safely if the model is missing, malformed, or uncertain.
    """

    user_text = " ".join(str(user_text).strip().split())

    if not user_text:
        return {
            "mode": "answer",
            "text": "No input provided."
        }

    # First handle deterministic compound commands.
    planned = plan_compound_request(user_text)
    if planned is not None:
        return planned

    try:
        # If model does not exist, use rule-based fallback.
        if not load_model_once():
            return safe_fallback(user_text)

        prompt = (
            "Translate the instruction into one valid JSON action.\n"
            "Return JSON only. Do not explain.\n"
            "Supported modes:\n"
            "- shell: {\"mode\":\"shell\",\"command\":\"...\"}\n"
            "- run_file: {\"mode\":\"run_file\",\"command\":\"...\"}\n"
            "- write_file: {\"mode\":\"write_file\",\"path\":\"...\",\"content\":\"...\"}\n"
            "- cd: {\"mode\":\"cd\",\"path\":\"...\"}\n"
            "- plan: {\"mode\":\"plan\",\"steps\":[...]}\n"
            "- answer: {\"mode\":\"answer\",\"text\":\"...\"}\n"
            f"Instruction: {user_text}\n"
            "JSON:"
        )

        inputs = _TOKENIZER(prompt, return_tensors="pt")
        inputs = {key: value.to(_DEVICE) for key, value in inputs.items()}

        with torch.no_grad():
            output = _MODEL.generate(
                **inputs,
                max_new_tokens=120,
                do_sample=True,
                temperature=0.25,
                top_p=0.9,
                repetition_penalty=1.15,
                pad_token_id=_TOKENIZER.eos_token_id,
                eos_token_id=_TOKENIZER.eos_token_id,
            )

        decoded = _TOKENIZER.decode(output[0], skip_special_tokens=True)

        # Optional but very useful while debugging:
        # print("MODEL RAW OUTPUT:", decoded, file=sys.stderr)

        generated_part = decoded[len(prompt):].strip()
        action = extract_first_json_object(generated_part)

        # Sometimes the model echoes the prompt, so try full decoded text too.
        if action is None:
            action = extract_first_json_object(decoded)

        if action is None:
            return safe_fallback(user_text)

        normalized = normalize_action(action)

        # If normalization failed, try fallback.
        if normalized.get("mode") == "answer":
            bad_messages = {
                "Model output was not a valid action object.",
                "Model returned an unsupported action mode.",
                "Model returned an invalid directory path.",
                "Model returned an empty execution plan.",
                "Model returned an invalid plan step.",
                "Nested plans are not supported.",
                "Model returned an empty command.",
                "Model returned an invalid file path.",
            }

            if normalized.get("text") in bad_messages:
                return safe_fallback(user_text)

        return normalized

    except Exception as e:
        print(f"Delphi inference error: {e}", file=sys.stderr)
        return safe_fallback(user_text)

def handle_request(user_text: str) -> dict:
    if not user_text:
        return {
            "mode": "answer",
            "text": "No input provided."
        }

    return generate_action(user_text)


def main():
    if len(sys.argv) < 2:
        print(json.dumps(handle_request(""), separators=(",", ":")))
        return

    user_text = " ".join(sys.argv[1:]).strip()
    action = handle_request(user_text)
    print(json.dumps(action, separators=(",", ":")))


if __name__ == "__main__":
    main()
