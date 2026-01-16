"""
Fine-tune Mistral 7B for SQL generation using QLoRA.
Optimized for running on a single A100 40GB or 2x RTX 4090.
"""

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune Mistral 7B for SQL")
    parser.add_argument("--model_name", default="mistralai/Mistral-7B-Instruct-v0.1")
    parser.add_argument("--dataset", default="b-mc2/sql-create-context")
    parser.add_argument("--output_dir", default="./mistral-7b-sql-lora")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--max_seq_length", type=int, default=2048)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    return parser.parse_args()


def create_quantization_config():
    """4-bit quantization for memory efficiency"""
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )


def create_lora_config(args):
    """LoRA configuration targeting attention layers"""
    return LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )


def format_sql_prompt(example):
    """Format training examples for SQL generation"""
    return f"""### Instruction:
Generate a SQL query for the following question based on the given schema.

### Schema:
{example['context']}

### Question:
{example['question']}

### SQL:
{example['answer']}"""


def main():
    args = parse_args()

    print(f"Loading model: {args.model_name}")

    # Load quantized model
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        quantization_config=create_quantization_config(),
        device_map="auto",
        trust_remote_code=True,
    )

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Prepare model for k-bit training
    model = prepare_model_for_kbit_training(model)

    # Apply LoRA
    lora_config = create_lora_config(args)
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load dataset
    print(f"Loading dataset: {args.dataset}")
    dataset = load_dataset(args.dataset, split="train")
    print(f"Dataset size: {len(dataset)} examples")

    # Training arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        learning_rate=args.learning_rate,
        fp16=True,
        logging_steps=100,
        save_strategy="epoch",
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        optim="paged_adamw_8bit",
        report_to="none",
    )

    # Initialize trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        formatting_func=format_sql_prompt,
        args=training_args,
        max_seq_length=args.max_seq_length,
        packing=False,
    )

    # Train
    print("Starting training...")
    trainer.train()

    # Save the LoRA adapter
    print(f"Saving model to {args.output_dir}")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    print("Training complete!")


if __name__ == "__main__":
    main()
