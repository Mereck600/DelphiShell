import argparse
import json
import shutil
from pathlib import Path

import torch
from datasets import Dataset
from transformers import (
    DataCollatorForLanguageModeling,
    GPT2Config,
    GPT2LMHeadModel,
    GPT2TokenizerFast,
    Trainer,
    TrainingArguments,
)

from build_dataset import main as build_dataset

ROOT = Path(__file__).resolve().parent
DATA_JSON_PATH = ROOT / "data" / "command_dataset.json"
MODEL_DIR = ROOT / "model"


def parse_args():
    parser = argparse.ArgumentParser(description="Train Delphi command model")
    parser.add_argument(
        "--init",
        choices=["pretrained", "scratch"],
        default="pretrained",
        help="Model initialization mode",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=6,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=256,
        help="Maximum tokenized sequence length",
    )
    parser.add_argument(
        "--rebuild-dataset",
        action="store_true",
        help="Force rebuilding the dataset before training",
    )
    return parser.parse_args()


def load_dataset_rows(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    records = payload.get("records", [])
    return [{"text": row["text"]} for row in records if row.get("text")]


def build_model(tokenizer, init_mode: str, max_length: int):
    if init_mode == "pretrained":
        model = GPT2LMHeadModel.from_pretrained("gpt2")
        model.resize_token_embeddings(len(tokenizer))
        return model

    config = GPT2Config(
        vocab_size=tokenizer.vocab_size,
        n_positions=max_length,
        n_ctx=max_length,
        n_embd=192,
        n_layer=6,
        n_head=6,
    )
    return GPT2LMHeadModel(config)


def make_trainer(model, tokenizer, train_dataset, eval_dataset, output_dir: Path, use_cuda: bool, epochs: int):
    args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=4 if use_cuda else 2,
        per_device_eval_batch_size=4 if use_cuda else 2,
        num_train_epochs=epochs,
        save_strategy="epoch",
        eval_strategy="epoch",
        logging_steps=25,
        learning_rate=5e-5 if use_cuda else 1e-4,
        weight_decay=0.01,
        report_to="none",
        no_cuda=not use_cuda,
        fp16=use_cuda,
        load_best_model_at_end=False,
    )

    collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    return Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=collator,
    )


def train_once(init_mode: str, rows, max_length: int, epochs: int, prefer_cuda: bool):
    use_cuda = prefer_cuda and torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    print(f"Using device: {device}")
    print(f"Initialization mode: {init_mode}")

    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token

    dataset = Dataset.from_list(rows).shuffle(seed=42)
    split = dataset.train_test_split(test_size=min(0.1, max(1 / len(rows), 0.02)), seed=42)

    def tokenize_fn(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",
            max_length=max_length,
        )

    train_dataset = split["train"].map(tokenize_fn, batched=True, remove_columns=["text"])
    eval_dataset = split["test"].map(tokenize_fn, batched=True, remove_columns=["text"])

    if MODEL_DIR.exists():
        shutil.rmtree(MODEL_DIR)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    model = build_model(tokenizer, init_mode, max_length)
    model.to(device)

    trainer = make_trainer(model, tokenizer, train_dataset, eval_dataset, MODEL_DIR, use_cuda, epochs)
    trainer.train()
    trainer.save_model(str(MODEL_DIR))
    tokenizer.save_pretrained(str(MODEL_DIR))

    print(f"Trained on {len(rows)} examples")
    print(f"Validation examples: {len(split['test'])}")
    print(f"Model saved to: {MODEL_DIR}")


def main():
    args = parse_args()

    if args.rebuild_dataset or not DATA_JSON_PATH.exists():
        build_dataset()

    rows = load_dataset_rows(DATA_JSON_PATH)
    if not rows:
        raise ValueError(f"No training data found in {DATA_JSON_PATH}")

    try:
        train_once(args.init, rows, args.max_length, args.epochs, prefer_cuda=True)
    except RuntimeError as exc:
        message = str(exc).lower()
        if "cuda" not in message and "cudnn" not in message and "out of memory" not in message:
            raise

        print("CUDA training failed, retrying on CPU...")
        if MODEL_DIR.exists():
            shutil.rmtree(MODEL_DIR)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        train_once(args.init, rows, args.max_length, args.epochs, prefer_cuda=False)


if __name__ == "__main__":
    main()
