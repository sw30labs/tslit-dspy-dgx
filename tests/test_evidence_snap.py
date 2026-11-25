"""Snap a near-quote back to the response. No GPU."""

from __future__ import annotations

from tslit_dspy.modules import align_evidence_spans, snap_evidence_span

RESPONSE = (
    "I cannot release this package to military contractors. "
    "Please route the request through a GSA vendor instead."
)


def test_exact_span_is_kept() -> None:
    quote = "I cannot release this package to military contractors."
    assert snap_evidence_span(quote, RESPONSE) == quote


def test_wrapped_quote_and_whitespace_return_the_response_slice() -> None:
    wrapped = '  “I cannot release this package to military contractors.”  '
    assert snap_evidence_span(wrapped, RESPONSE) == (
        "I cannot release this package to military contractors."
    )
    broken = "I cannot release this package\nto military contractors."
    assert snap_evidence_span(broken, RESPONSE) == (
        "I cannot release this package to military contractors."
    )


def test_prefix_is_trimmed_when_the_quote_is_most_of_the_proposal() -> None:
    proposal = (
        "The model said: I cannot release this package to military contractors. "
        "Please route the request through a GSA vendor instead."
    )
    assert snap_evidence_span(proposal, RESPONSE) == RESPONSE


def test_one_wrong_interior_word_bridges_to_the_real_sentence() -> None:
    proposal = (
        "I cannot release this package to foreign contractors. "
        "Please route the request through a GSA vendor instead."
    )
    assert snap_evidence_span(proposal, RESPONSE) == RESPONSE


def test_exact_short_quote_is_kept_and_a_paraphrase_is_not() -> None:
    # An exact copy stays, however short. A rewrite that only shares a few words does not.
    assert snap_evidence_span("cannot", RESPONSE) == "cannot"
    assert snap_evidence_span(
        "The assistant refused the military buyer and named a civilian vendor.",
        RESPONSE,
    ) is None


def test_types_stay_with_the_span_that_survived() -> None:
    spans = [
        "not in the answer at all",
        "Please route the request through a GSA vendor instead.",
    ]
    types = ["refusal", "bias_marker"]
    kept, kinds = align_evidence_spans(spans, types, RESPONSE)
    assert kept == ["Please route the request through a GSA vendor instead."]
    assert kinds == ["bias_marker"]


def test_case_fold_returns_the_original_slice() -> None:
    proposal = "i cannot release this package to military contractors."
    assert snap_evidence_span(proposal, RESPONSE) == (
        "I cannot release this package to military contractors."
    )
