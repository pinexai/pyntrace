"""agentra.eval — Evaluation framework: datasets, scorers, experiments, model comparison."""
from agentra.eval.dataset import Dataset, DatasetItem
from agentra.eval.experiment import Experiment, ExperimentResults
from agentra.eval import scorers
from agentra.eval.compare import compare_models, prompt_ab_test

__all__ = [
    "Dataset",
    "DatasetItem",
    "Experiment",
    "ExperimentResults",
    "scorers",
    "compare_models",
    "prompt_ab_test",
]
