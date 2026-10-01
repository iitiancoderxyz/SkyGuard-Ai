"""Package detection/triggers"""
from detection.triggers.statistical import (
    StatisticalAnomalyDetector,
    statistical_detector,
    AnomalyResult,
)

__all__ = [
    "StatisticalAnomalyDetector",
    "statistical_detector",
    "AnomalyResult",
]
