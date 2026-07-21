"""
TSLIT-DSPy: DSPy-compiled threat detection pipeline for TSLIT (DGX port).

Detection stack must use non-adversary / American models only.
See model_policy.py.
"""

__version__ = "0.2.0"
__author__ = "Nicolas Cravino"

from tslit_dspy.schemas import AnalysisResult

# Lazy-heavy imports: dspy is only required when constructing the analyzer.
def __getattr__(name: str):
    if name == "TSLITAnalyzer":
        from tslit_dspy.modules import TSLITAnalyzer

        return TSLITAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["TSLITAnalyzer", "AnalysisResult", "__version__"]
