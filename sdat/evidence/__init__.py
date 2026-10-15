"""SDAT Evidence Aggregator package.

Provides correlation, concept indexing, absence synthesis, and packaging
of EvidenceFacts into EvidenceBundles for downstream agent evaluation.
"""

from .aggregator import EvidenceAggregator

__all__ = ["EvidenceAggregator"]
