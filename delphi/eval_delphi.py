import json
from pathlib import Path

from infer_delphi import generate_action

ROOT = Path(__file__).resolve().parent
EVAL_PATH = ROOT / "data" / "eval_dataset.json"


def load_eval_rows(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("records", [])


def main():
    rows = load_eval_rows(EVAL_PATH)
    if not rows:
        raise ValueError(f"No eval data found in {EVAL_PATH}")

    total = len(rows)
    exact_matches = 0
    mode_matches = 0
    failures = []

    for row in rows:
        instruction = row["instruction"]
        expected = row["action"]
        predicted = generate_action(instruction)

        if predicted.get("mode") == expected.get("mode"):
            mode_matches += 1

        if predicted == expected:
            exact_matches += 1
        else:
            failures.append(
                {
                    "instruction": instruction,
                    "expected": expected,
                    "predicted": predicted,
                }
            )

    print(f"Eval examples: {total}")
    print(f"Mode accuracy: {mode_matches}/{total} = {mode_matches / total:.1%}")
    print(f"Exact accuracy: {exact_matches}/{total} = {exact_matches / total:.1%}")

    if failures:
        print("Failures:")
        for failure in failures[:10]:
            print(json.dumps(failure, indent=2))


if __name__ == "__main__":
    main()
