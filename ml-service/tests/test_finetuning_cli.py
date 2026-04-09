"""Tests for fine-tuning CLI entry point."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from modelforge.finetuning.cli import (
    build_parser,
    main,
    cmd_train,
    cmd_evaluate,
    cmd_list_versions,
    cmd_activate,
    _build_finetuning_config,
    _build_training_config,
)


# === Parser tests ===


class TestBuildParser:
    def test_train_command_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["train"])
        assert args.command == "train"
        assert args.epochs == 50
        assert args.learning_rate == 1e-4
        assert args.lr_schedule == "cosine"
        assert args.batch_size == 4
        assert args.register is True
        assert args.resume is False
        assert args.activate is False

    def test_train_command_custom_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "train",
            "--dataset-root", "/data/custom",
            "--epochs", "100",
            "--learning-rate", "0.001",
            "--lr-schedule", "step",
            "--batch-size", "8",
            "--checkpoint-dir", "/tmp/ckpt",
            "--resume",
            "--patience", "5",
            "--categories", "chair", "table",
            "--activate",
            "--no-register",
        ])
        assert args.dataset_root == "/data/custom"
        assert args.epochs == 100
        assert args.learning_rate == 0.001
        assert args.lr_schedule == "step"
        assert args.batch_size == 8
        assert args.checkpoint_dir == "/tmp/ckpt"
        assert args.resume is True
        assert args.patience == 5
        assert args.categories == ["chair", "table"]
        assert args.activate is True
        assert args.register is False

    def test_evaluate_command(self):
        parser = build_parser()
        args = parser.parse_args([
            "evaluate",
            "--dataset-root", "/data/test",
            "--max-samples", "10",
            "--output", "/tmp/report.json",
        ])
        assert args.command == "evaluate"
        assert args.dataset_root == "/data/test"
        assert args.max_samples == 10
        assert args.output == "/tmp/report.json"

    def test_list_versions_command(self):
        parser = build_parser()
        args = parser.parse_args(["list-versions", "--checkpoint-dir", "/tmp/ckpt"])
        assert args.command == "list-versions"
        assert args.checkpoint_dir == "/tmp/ckpt"

    def test_activate_command(self):
        parser = build_parser()
        args = parser.parse_args(["activate", "finetuned-v1", "--checkpoint-dir", "/tmp/ckpt"])
        assert args.command == "activate"
        assert args.version == "finetuned-v1"

    def test_no_command_returns_1(self):
        result = main([])
        assert result == 1


# === Config builders ===


class TestConfigBuilders:
    def test_build_finetuning_config(self):
        parser = build_parser()
        args = parser.parse_args([
            "train",
            "--dataset-root", "/data/shapenet",
            "--batch-size", "8",
            "--seed", "123",
            "--categories", "chair",
        ])
        config = _build_finetuning_config(args)
        assert config.dataset_root == Path("/data/shapenet")
        assert config.batch_size == 8
        assert config.seed == 123
        assert config.categories == ["chair"]

    def test_build_training_config(self):
        parser = build_parser()
        args = parser.parse_args([
            "train",
            "--epochs", "20",
            "--learning-rate", "0.001",
            "--lr-schedule", "step",
            "--checkpoint-dir", "/tmp/ckpt",
            "--checkpoint-every", "10",
            "--resume",
            "--patience", "5",
            "--chamfer-weight", "2.0",
            "--edge-weight", "0.2",
            "--laplacian-weight", "0.1",
        ])
        config = _build_training_config(args)
        assert config.num_epochs == 20
        assert config.learning_rate == 0.001
        assert config.lr_schedule == "step"
        assert config.checkpoint_dir == Path("/tmp/ckpt")
        assert config.checkpoint_every == 10
        assert config.resume_from_checkpoint is True
        assert config.early_stopping_patience == 5
        assert config.chamfer_weight == 2.0
        assert config.edge_weight == 0.2
        assert config.laplacian_weight == 0.1


# === Command tests ===


class TestCmdTrain:
    @patch("modelforge.finetuning.cli.TripoSRTrainer")
    def test_train_success(self, mock_trainer_cls, tmp_path):
        mock_trainer = MagicMock()
        mock_trainer.train.return_value = [MagicMock(train_loss=0.5)]
        mock_trainer.get_training_summary.return_value = {
            "total_epochs": 5,
            "best_val_loss": 0.5,
        }
        mock_trainer_cls.return_value = mock_trainer

        result = main([
            "train",
            "--dataset-root", str(tmp_path),
            "--epochs", "5",
            "--checkpoint-dir", str(tmp_path / "ckpt"),
            "--no-register",
        ])

        assert result == 0
        mock_trainer_cls.assert_called_once()
        mock_trainer.train.assert_called_once()

        # Verify summary file was written
        summary_path = tmp_path / "ckpt" / "training_summary.json"
        assert summary_path.exists()

    @patch("modelforge.finetuning.cli.TripoSRTrainer")
    def test_train_empty_dataset_returns_1(self, mock_trainer_cls, tmp_path):
        mock_trainer = MagicMock()
        mock_trainer.train.return_value = []
        mock_trainer_cls.return_value = mock_trainer

        result = main([
            "train",
            "--dataset-root", str(tmp_path),
            "--epochs", "5",
            "--checkpoint-dir", str(tmp_path / "ckpt"),
            "--no-register",
        ])

        assert result == 1

    @patch("modelforge.finetuning.cli.WeightManager")
    @patch("modelforge.finetuning.cli.TripoSRTrainer")
    def test_train_with_register_and_activate(self, mock_trainer_cls, mock_wm_cls, tmp_path):
        mock_trainer = MagicMock()
        mock_trainer.train.return_value = [MagicMock(train_loss=0.3)]
        mock_trainer.get_training_summary.return_value = {"total_epochs": 1}
        mock_trainer_cls.return_value = mock_trainer

        mock_wm = MagicMock()
        mock_wm.auto_register_from_training.return_value = "finetuned-v1"
        mock_wm_cls.return_value = mock_wm

        result = main([
            "train",
            "--dataset-root", str(tmp_path),
            "--epochs", "5",
            "--checkpoint-dir", str(tmp_path / "ckpt"),
            "--register",
            "--activate",
        ])

        assert result == 0
        mock_wm.auto_register_from_training.assert_called_once()
        mock_wm.set_active_version.assert_called_once_with("finetuned-v1")


class TestCmdEvaluate:
    @patch("modelforge.finetuning.cli.FinetuningEvaluator")
    def test_evaluate_success(self, mock_eval_cls, tmp_path):
        mock_report = MagicMock()
        mock_report.summary.return_value = "=== Evaluation Report ==="

        mock_eval = MagicMock()
        mock_eval.evaluate_from_test_split.return_value = mock_report
        mock_eval_cls.return_value = mock_eval

        output_path = tmp_path / "report.json"
        result = main([
            "evaluate",
            "--dataset-root", str(tmp_path),
            "--output", str(output_path),
            "--max-samples", "5",
        ])

        assert result == 0
        mock_eval.evaluate_from_test_split.assert_called_once_with(
            base_version="base",
            finetuned_version="finetuned",
            max_samples=5,
        )
        mock_report.save.assert_called_once_with(output_path)


class TestCmdListVersions:
    def test_list_versions_no_dir(self, tmp_path):
        result = main(["list-versions", "--checkpoint-dir", str(tmp_path / "nonexistent")])
        assert result == 0

    def test_list_versions_empty(self, tmp_path):
        result = main(["list-versions", "--checkpoint-dir", str(tmp_path)])
        assert result == 0

    def test_list_versions_with_registered(self, tmp_path):
        from modelforge.finetuning.weight_manager import WeightManager

        wm = WeightManager(checkpoint_dir=tmp_path)
        wm.register_checkpoint(
            version_id="test-v1",
            checkpoint_path=str(tmp_path / "v1"),
            description="Test version",
            val_loss=0.123,
            training_epochs=10,
        )

        result = main(["list-versions", "--checkpoint-dir", str(tmp_path)])
        assert result == 0


class TestCmdActivate:
    def test_activate_base(self, tmp_path):
        result = main(["activate", "base", "--checkpoint-dir", str(tmp_path)])
        assert result == 0

    def test_activate_unknown_version(self, tmp_path):
        result = main(["activate", "nonexistent", "--checkpoint-dir", str(tmp_path)])
        assert result == 1
