import os
import json
import shutil
from pathlib import Path

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
from build_dataset import main as build_dataset

ROOT = Path(__file__).resolve().parent
DATA_JSON_PATH = ROOT / "data" / "command_dataset.json"
MODEL_DIR = ROOT / "model"


def load_dataset_rows(path: Path):
    # Loads the generated JSON dataset and returns the language-model training rows.
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    records = payload.get("records", [])
    rows = [{"text": row["text"]} for row in records if row.get("text")]
    return rows


def main():
    # Rebuilds the dataset, trains a small GPT-2 style model, and saves both
    # the model weights and tokenizer for local inference.
    print(torch.__version__)
    print(torch.version.cuda)
    print(torch.cuda.is_available())
    print(torch.cuda.device_count())
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")


    print(f"Using device: {device}")
    build_dataset()

    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token

    config = GPT2Config(
        vocab_size=tokenizer.vocab_size,
        n_positions=192,
        n_ctx=192,
        n_embd=128,
        n_layer=4,
        n_head=4,
    )

    model = GPT2LMHeadModel(config)
    model.to(device)

    rows = load_dataset_rows(DATA_JSON_PATH)
    if not rows:
        raise ValueError(f"No training data found in {DATA_JSON_PATH}")

    dataset = Dataset.from_list(rows)

    def tokenize_fn(examples):
        # Converts raw text examples into fixed-length token sequences for training.
        return tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",
            max_length=192,
        )

    tokenized = dataset.map(tokenize_fn, batched=True, remove_columns=["text"])

    model_dir = MODEL_DIR
    if model_dir.exists():
        shutil.rmtree(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    args = TrainingArguments(
        output_dir=str(model_dir),
        per_device_train_batch_size=8,
        num_train_epochs=6,
        save_strategy="epoch",
        logging_steps=10,
        learning_rate=3e-4,
        weight_decay=0.01,
        report_to="none",
        no_cuda=not use_cuda,
        fp16=use_cuda,
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
