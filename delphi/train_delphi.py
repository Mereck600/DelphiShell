import os
import json
import shutil
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
from datasets import Dataset
from transformers import (
    GPT2Config,
    GPT2LMHeadModel,
    GPT2TokenizerFast,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
)

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "commands.jsonl"
MODEL_DIR = ROOT / "model"


def load_jsonl(path: Path):
    # Loads line-delimited JSON training rows from disk into a Python list.
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    # Builds a small GPT-2 style model, trains it on the command dataset, and
    # saves both the model weights and tokenizer for local inference.
    print("Using device: cpu")

    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token

    config = GPT2Config(
        vocab_size=tokenizer.vocab_size,
        n_positions=128,
        n_ctx=128,
        n_embd=128,
        n_layer=4,
        n_head=4,
    )

    model = GPT2LMHeadModel(config)
    model.to(torch.device("cpu"))

    rows = load_jsonl(DATA_PATH)
    if not rows:
        raise ValueError(f"No training data found in {DATA_PATH}")

    dataset = Dataset.from_list(rows)

    def tokenize_fn(examples):
        # Converts raw text examples into fixed-length token sequences for training.
        return tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",
            max_length=128,
        )

    tokenized = dataset.map(tokenize_fn, batched=True, remove_columns=["text"])

    model_dir = MODEL_DIR
    if model_dir.exists():
        shutil.rmtree(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    args = TrainingArguments(
        output_dir=str(model_dir),
        per_device_train_batch_size=2,
        num_train_epochs=10,
        save_strategy="epoch",
        logging_steps=1,
        learning_rate=5e-4,
        weight_decay=0.01,
        report_to="none",
        no_cuda=True,
    )

    collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized,
        data_collator=collator,
    )

    trainer.train()
    trainer.save_model(str(model_dir))
    tokenizer.save_pretrained(str(model_dir))

    print(f"Model saved to: {model_dir}")


if __name__ == "__main__":
    main()
