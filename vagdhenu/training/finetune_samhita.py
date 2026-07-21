#!/usr/bin/env python3
"""finetune_samhita.py — Fine-tune IndicF5 on the Samhita Corpus.

This script loads the pre-trained IndicF5 checkpoint, initializes the flow-matching
Transformer (DiT), and starts the voice-steer fine-tuning run.

Run with Accelerate DDP:
    accelerate launch vagdhenu/training/finetune_samhita.py \\
      --vocab models/vocab.txt \\
      --warm models/indicf5_sanskrit_base.pt \\
      --data_dir data/samhita_training \\
      --save_dir models/samhita_champion/ \\
      --wandb_name samhita-run-1
"""

import argparse
import sys
from pathlib import Path
import torch

# Add vagdhenu/IndicF5 to path for model/trainer imports
vagdhenu_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(vagdhenu_root / "IndicF5"))

try:
    from f5_tts.infer.utils_infer import load_model
    from f5_tts.model import DiT, Trainer
    from f5_tts.model.dataset import load_dataset
except ImportError:
    print("ERROR: Could not import F5-TTS libraries. Ensure setup.sh has run successfully.")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Fine-tune IndicF5 on Samhita Corpus")
    ap.add_argument("--vocab", required=True, help="Path to vocab.txt file")
    ap.add_argument("--warm", required=True, help="Path to pre-trained base .pt checkpoint")
    ap.add_argument("--data_dir", required=True, help="Preprocessed training data folder")
    ap.add_argument("--save_dir", required=True, help="Directory to save checkpoints")
    ap.add_argument("--wandb_name", required=True, help="Weights & Biases run name")
    ap.add_argument("--epochs", type=int, default=300, help="Number of training epochs")
    ap.add_argument("--lr", type=float, default=1e-5, help="Learning rate (default: 1e-5 for fine-tune)")
    ap.add_argument("--bs", type=int, default=19200, help="Frame batch size (default: 19200)")
    ap.add_argument("--save_per", type=int, default=1000, help="Save checkpoint every N steps")
    args = ap.parse_args()

    # Base DiT Configuration matched to Vāgdhenu champion parameters
    CFG = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
    
    print(f"Loading base checkpoint: {args.warm}")
    cfm = load_model(DiT, CFG, mel_spec_type="vocos", vocab_file=args.vocab, device="cpu")
    ck = torch.load(args.warm, map_location="cpu", weights_only=True)
    sd = ck.get("model_state_dict", ck)
    
    # Warm-start base model
    miss, unexp = cfm.load_state_dict(sd, strict=False)
    print(f"[warm-start] non-melspec missing: {len([m for m in miss if 'mel_spec' not in m])} | unexpected: {len(unexp)}")

    # Initialize F5-TTS Trainer
    trainer = Trainer(
        cfm,
        epochs=args.epochs,
        learning_rate=args.lr,
        num_warmup_updates=500,
        save_per_updates=args.save_per,
        last_per_steps=args.save_per,
        checkpoint_path=args.save_dir,
        batch_size=args.bs,
        batch_size_type="frame",
        max_samples=64,
        grad_accumulation_steps=1,
        max_grad_norm=1.0,
        logger="wandb",
        wandb_project="indicf5-samhita",
        wandb_run_name=args.wandb_name,
        mel_spec_type="vocos",
        log_samples=False,
    )

    # Audio/Mel-Spectrogram settings matched to Vāgdhenu F5 configurations
    MELKW = dict(
        n_fft=1024,
        hop_length=256,
        win_length=1024,
        n_mel_channels=100,
        target_sample_rate=24000,
        mel_spec_type="vocos"
    )

    print(f"Loading custom dataset from: {args.data_dir}")
    train_dataset = load_dataset(
        "indicf5",
        "custom",
        dataset_type="CustomDatasetPath",
        mel_spec_kwargs=MELKW,
        data_dir=args.data_dir
    )

    print("Starting training run...")
    trainer.train(train_dataset)


if __name__ == "__main__":
    main()
