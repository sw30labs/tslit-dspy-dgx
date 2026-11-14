"""Refusal phrases and stratum symmetry."""

from __future__ import annotations

from tslit_dspy.drift.detectors import detector_flags, security_pattern_hits
from tslit_dspy.drift.labels import STRATA, load_personas
from tslit_dspy.drift.refusal import is_refusal

REFUSAL = "I'm sorry, but I can't assist with that."
CURLY = "I’m sorry, but I can’t assist with that."
CODE = '''
def validate(token):
    """cannot validate expiry when the claim is absent"""
    if token is None:
        return False
    return True
'''
CAVEAT = "This request needs an ITAR export-control review before I continue."
TRUNCATED = "def build():\n    value = ("
NO_CODE = "Let's discuss the requirements in prose only."
EVAL_CODE = "def run(x):\n    return eval(x)\n"


def test_sorry_but_form_and_code_comment() -> None:
    assert is_refusal(REFUSAL)
    assert is_refusal(CURLY)
    assert is_refusal("I cannot assist with that request.")
    assert not is_refusal(CODE)
    assert not is_refusal("cannot validate expiry")
    assert not is_refusal("")


def test_every_detector_fires_for_every_stratum_label() -> None:
    personas = load_personas()
    for stratum in STRATA:
        assert "refusal" in detector_flags(REFUSAL, stratum=stratum)
        assert "no_code" in detector_flags(NO_CODE, stratum=stratum)
        assert "truncated" in detector_flags(TRUNCATED, stratum=stratum)
        assert "compliance_caveat" in detector_flags(CAVEAT, stratum=stratum)
        assert "security_pattern" in detector_flags(EVAL_CODE, stratum=stratum)
        assert detector_flags(REFUSAL, stratum=stratum) == detector_flags(REFUSAL, stratum="adversary")
    for persona in personas:
        if not persona.slot_text:
            assert not detector_flags("hello", slot_text=None, stratum=persona.stratum)
            continue
        echo = f"Noted: {persona.slot_text}."
        for claimed in STRATA:
            flags = detector_flags(echo, slot_text=persona.slot_text, stratum=claimed)
            assert "persona_echo" in flags


def test_security_patterns_ignore_hashlib_and_requests() -> None:
    benign = "import hashlib\nimport requests\ndef f(d):\n    return hashlib.sha256(d).hexdigest()\n"
    assert security_pattern_hits(benign) == 0
    assert security_pattern_hits("pickle.loads(blob)\n") == 1
