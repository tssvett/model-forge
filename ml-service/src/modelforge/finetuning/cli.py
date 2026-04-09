#!/usr/bin/env python3
"""CLI entry point for TripoSR fine-tuning pipeline.

Orchestrates: configure -> load dataset -> train -> evaluate -> register weights.
Can be invoked from command line or Docker.

Usage:
    python -m modelforge.finetuning.cli train --dataset-root data/shapenet --epochs 50
    python -m modelforge.finetuning.cli evaluate --checkpoint-dir checkpoints/triposr
    python -m modelforge.finetuning.cli list-versions --checkpoint-dir checkpoints/triposr
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

from .config import FinetuningConfig, TrainingConfig
from .training import TripoSRTrainer
from .evaluation import FinetuningEvaluator
from .weight_manager import WeightManager

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI usage."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def _build_finetuning_config(args: argparse.Namespace) -> FinetuningConfig:
    """Build FinetuningConfig from CLI arguments."""
    kwargs = {
        "dataset_root": Path(args.dataset_root),
        "batch_size": args.batch_size,
        "seed": args.seed,
    }
    if args.categories:
        kwargs["categories"] = args.categories
    if args.image_size:
        kwargs["image_size"] = args.image_size
    return FinetuningConfig(**kwargs)


def _build_training_config(args: argparse.Namespace) -> TrainingConfig:
    """Build TrainingConfig from CLI arguments."""
    return TrainingConfig(
        num_epochs=args.epochs,
        learning_rate=args.learning_rate,
        lr_schedule=args.lr_schedule,
        checkpoint_dir=Path(args.checkpoint_dir),
        checkpoint_every=args.checkpoint_every,
        resume_from_checkpoint=args.resume,
        early_stopping_patience=args.patience,
        chamfer_weight=args.chamfer_weight,
        edge_weight=args.edge_weight,
        laplacian_weight=args.laplacian_weight,
    )


def cmd_train(args: argparse.Namespace) -> int:
    """Run the fine-tuning training pipeline."""
    ft_config = _build_finetuning_config(args)
    tr_config = _build_training_config(args)

    logger.info("Starting fine-tuning training pipeline")
    logger.info("Dataset: %s", ft_config.dataset_root)
    logger.info("Epochs: %d, LR: %.6f, Schedule: %s",
                tr_config.num_epochs, tr_config.learning_rate, tr_config.lr_schedule)
    logger.info("Checkpoints: %s", tr_config.checkpoint_dir)

    start_time = time.time()

    trainer = TripoSRTrainer(
        finetuning_config=ft_config,
        training_config=tr_config,
    )

    metrics_history = trainer.train()

    if not metrics_history:
        logger.error("Training produced no results (empty dataset?)")
        return 1

    summary = trainer.get_training_summary()
    elapsed = time.time() - start_time

    logger.info("Training complete in %.1fs", elapsed)
    logger.info("Summary: %s", json.dumps(summary, indent=2))

    # Auto-register checkpoint
    if args.register:
        weight_manager = WeightManager(checkpoint_dir=tr_config.checkpoint_dir)
        version_id = weight_manager.auto_register_from_training(tr_config.checkpoint_dir)
        if version_id:
            logger.info("Registered model version: %s", version_id)
            if args.activate:
                weight_manager.set_active_version(version_id)
                logger.info("Activated version: %s", version_id)
        else:
            logger.warning("Failed to auto-register checkpoint")

    # Save training summary
    summary_path = tr_config.checkpoint_dir / "training_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info("Training summary saved to %s", summary_path)

    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Run evaluation comparing base vs fine-tuned model."""
    ft_config = _build_finetuning_config(args)

    logger.info("Starting evaluation pipeline")
    logger.info("Dataset: %s", ft_config.dataset_root)

    evaluator = FinetuningEvaluator(
        finetuning_config=ft_config,
        num_surface_samples=args.num_surface_samples,
    )

    report = evaluator.evaluate_from_test_split(
        base_version=args.base_version,
        finetuned_version=args.finetuned_version,
        max_samples=args.max_samples,
    )

    # Print summary
    print(report.summary())

    # Save report
    if args.output:
        output_path = Path(args.output)
        report.save(output_path)
        logger.info("Report saved to %s", output_path)

    return 0


def cmd_list_versions(args: argparse.Namespace) -> int:
    """List registered model versions."""
    checkpoint_dir = Path(args.checkpoint_dir)
    if not checkpoint_dir.exists():
        logger.info("Checkpoint directory does not exist: %s", checkpoint_dir)
        return 0

    weight_manager = WeightManager(checkpoint_dir=checkpoint_dir)
    versions = weight_manager.list_versions()
    active = weight_manager.get_active_version()

    if not versions:
        print("No registered model versions.")
        print(f"Active: {active} (base model)")
        return 0

    print(f"Active version: {active}")
    print(f"Registered versions ({len(versions)}):")
    print("-" * 60)
    for v in versions:
        marker = " *" if v.version_id == active else "  "
        val_loss_str = f"val_loss={v.val_loss:.6f}" if v.val_loss is not None else "val_loss=N/A"
        epochs_str = f"epochs={v.training_epochs}" if v.training_epochs else ""
        print(f"{marker} {v.version_id}: {v.description} ({val_loss_str}, {epochs_str})")

    # Check for unregistered checkpoints
    discovered = weight_manager.discover_checkpoints()
    if discovered:
        print(f"\nUnregistered checkpoints found ({len(discovered)}):")
        for path in discovered:
            print(f"  - {path}")

    return 0


def cmd_activate(args: argparse.Namespace) -> int:
    """Set the active model version."""
    weight_manager = WeightManager(checkpoint_dir=Path(args.checkpoint_dir))

    try:
        weight_manager.set_active_version(args.version)
        print(f"Active version set to: {args.version}")
        return 0
    except ValueError as e:
        logger.error(str(e))
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="modelforge-finetune",
        description="TripoSR fine-tuning pipeline CLI",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # === train ===
    train_parser = subparsers.add_parser("train", help="Run fine-tuning training")
    # Dataset args
    train_parser.add_argument("--dataset-root", type=str, default="data/shapenet",
                              help="Path to dataset root directory")
    train_parser.add_argument("--categories", nargs="+", default=None,
                              help="ShapeNet categories to train on")
    train_parser.add_argument("--batch-size", type=int, default=4)
    train_parser.add_argument("--image-size", type=int, default=None)
    train_parser.add_argument("--seed", type=int, default=42)
    # Training args
    train_parser.add_argument("--epochs", type=int, default=50)
    train_parser.add_argument("--learning-rate", type=float, default=1e-4)
    train_parser.add_argument("--lr-schedule", choices=["cosine", "step", "constant"],
                              default="cosine")
    train_parser.add_argument("--checkpoint-dir", type=str, default="checkpoints/triposr")
    train_parser.add_argument("--checkpoint-every", type=int, default=5)
    train_parser.add_argument("--resume", action="store_true",
                              help="Resume from latest checkpoint")
    train_parser.add_argument("--patience", type=int, default=10,
                              help="Early stopping patience (0 to disable)")
    # Loss weights
    train_parser.add_argument("--chamfer-weight", type=float, default=1.0)
    train_parser.add_argument("--edge-weight", type=float, default=0.1)
    train_parser.add_argument("--laplacian-weight", type=float, default=0.05)
    # Post-training
    train_parser.add_argument("--register", action="store_true", default=True,
                              help="Auto-register checkpoint after training")
    train_parser.add_argument("--no-register", dest="register", action="store_false")
    train_parser.add_argument("--activate", action="store_true",
                              help="Set trained version as active after training")

    # === evaluate ===
    eval_parser = subparsers.add_parser("evaluate", help="Run evaluation pipeline")
    eval_parser.add_argument("--dataset-root", type=str, default="data/shapenet")
    eval_parser.add_argument("--categories", nargs="+", default=None)
    eval_parser.add_argument("--batch-size", type=int, default=4)
    eval_parser.add_argument("--image-size", type=int, default=None)
    eval_parser.add_argument("--seed", type=int, default=42)
    eval_parser.add_argument("--checkpoint-dir", type=str, default="checkpoints/triposr")
    eval_parser.add_argument("--base-version", type=str, default="base")
    eval_parser.add_argument("--finetuned-version", type=str, default="finetuned")
    eval_parser.add_argument("--max-samples", type=int, default=None)
    eval_parser.add_argument("--num-surface-samples", type=int, default=10000)
    eval_parser.add_argument("--output", type=str, default=None,
                              help="Path to save evaluation report JSON")

    # === list-versions ===
    list_parser = subparsers.add_parser("list-versions", help="List registered model versions")
    list_parser.add_argument("--checkpoint-dir", type=str, default="checkpoints/triposr")

    # === activate ===
    act_parser = subparsers.add_parser("activate", help="Set active model version")
    act_parser.add_argument("version", type=str, help="Version ID to activate")
    act_parser.add_argument("--checkpoint-dir", type=str, default="checkpoints/triposr")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    _setup_logging(verbose=args.verbose)

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "train": cmd_train,
        "evaluate": cmd_evaluate,
        "list-versions": cmd_list_versions,
        "activate": cmd_activate,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
