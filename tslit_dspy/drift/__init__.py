"""Adversary-affiliation drift instrument.

Measurement only: matched affiliation swaps, executable oracles, pre-registered
contrasts. Not a Magika choke and not a detector-training set.

``relation_to_model_origin`` is relative to a China-origin target. See
``config/drift/personas.yaml`` and ``docs/drift/adversary-definition.md``.
"""

INSTRUMENT = "adversary-drift-v2"

__all__ = ["INSTRUMENT"]
