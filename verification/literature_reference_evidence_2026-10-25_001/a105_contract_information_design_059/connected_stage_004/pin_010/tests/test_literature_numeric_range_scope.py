"""Synthetic finite range/coordination contrasts; no scientific interpretation."""
from copy import deepcopy
import hashlib

import pytest

from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_partner_source_fields import (
    _between_numeric_scope, _relation, read_source_number,
)
from gene_annotation_episode.literature_rate_native_inputs import _number


ALLOCATION = ("The mix was divided between two vessels of 180 μl each and "
    "3.2 μM enzyme A and 4.6 μM enzyme B were added to the respective vessels.")
THREE = ("The buffer was distributed between three wells, and "
    "3.2 μM A, 4.6 μM B and 5.1 μM C were added to their respective wells.")


def select(text, token, *, quote=None, occurrence=0):
    """Keep the real full source even when the witness is only a scalar."""
    first = -1
    for _ in range(occurrence + 1):
        first = text.index(token, first + 1)
    quote = token if quote is None else quote
    left = first if quote == token else text.index(quote)
    offset = first - left
    witness = {"source_ref": "source_synthetic", "representation": "original",
        "start": len(text[:left].encode()), "end": len(text[:left + len(quote)].encode()), "quote": quote}
    return {"witness": witness, "number_start": offset, "number_end": offset + len(token)}


def scalar(text, token, *, native, quote=None, role="rate", occurrence=0):
    selected = select(text, token, quote=quote, occurrence=occurrence)
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_" + hashlib.sha256(text.encode()).hexdigest(),
        "content": text.encode()})
    return (_number(selected, sources, role) if native else
        read_source_number(selected, sources=sources, role=role))


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("text,tokens", [(ALLOCATION, ["3.2", "4.6"]), (THREE, ["3.2", "4.6", "5.1"]),
    ("A received 3.2 μM and B received 4.6 μM.", ["3.2", "4.6"])])
@pytest.mark.parametrize("full_witness", [False, True])
def test_review028_positive_and_ordinary_contrasts(text, tokens, native, full_witness):
    for token in tokens:
        row = scalar(text, token, native=native, quote=text if full_witness else None)
        assert row["relation"] == "point" and row["value"] == float(token)
        assert row["selector"]["witness"]["quote"] == (text if full_witness else token)


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("phrase,tokens", [
    ("The concentration was between 3.2 and 4.6 μM.", ["3.2", "4.6"]),
    ("The concentration was between approximately 3.2 μM and 4.6 μM.", ["3.2", "4.6"]),
    ("between 3.2 μM A and 4.6 μM B", ["3.2", "4.6"]),
    ("between a low concentration and 4.6 μM", ["4.6"]),
    ("between 3.2 on day one and 4.6 μM on day two", ["3.2", "4.6"]),
    ("between unusually low 3.2 and 4.6 μM", ["3.2", "4.6"]),
    ("between an unfamiliar first endpoint of 3.2 μM and 4.6 μM", ["3.2", "4.6"]),
    ("between approx. 3.2 and 4.6 μM", ["3.2", "4.6"]),
    ("between 3.e2 and 4.6e2 μM", ["3.e2", "4.6e2"]),
    ("The mix was divided between two vessels and 3.2–4.6 μM A was added.", ["3.2", "4.6"]),
    ("The mix was divided between two vessels and 3.2 to 4.6 μM A was added.", ["3.2", "4.6"]),
])
def test_review028_interval_and_unknown_contrasts_reject_both_endpoints(phrase, tokens, native):
    for token in tokens:
        with pytest.raises(ExperimentalContractError, match="interval_source_number|approximate_source_number"):
            scalar(phrase, token, native=native)


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("body", [
    "between 3.2 μM A and 4.6 μM B",
    "between unusually low 3.2 μM A and 4.6 μM B",
    "3.2 to 4.6 μM A", "3.2–4.6 μM A", "from 3.2 to 4.6 μM A",
    "3.2 μM A and between 4.6 and 5.1 μM B",
])
def test_completed_allocation_cannot_hide_a_later_real_interval(body, native):
    text = "The mix was divided between 12 flasks and " + body + " were added to the respective flasks."
    for token in ("3.2", "4.6"):
        with pytest.raises(ExperimentalContractError, match="interval_source_number"):
            scalar(text, token, native=native)


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("count", ["2", "17", "109", "two", "seventeen", "twenty-one"])
@pytest.mark.parametrize("size", [1, 2, 3, 7])
def test_digit_and_spelled_counts_and_arbitrary_list_positions(count, size, native):
    tokens = [f"{i + 3}.2" for i in range(size)]
    parts = [f"{token} μM enzyme Q{chr(65 + i)}" for i, token in enumerate(tokens)]
    body = parts[0] if size == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    text = f"The buffer was evenly distributed between {count} wells, and {body} were added to their respective wells."
    for token in tokens:
        assert scalar(text, token, native=native)["relation"] == "point"


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("modification", [
    lambda s: s.replace("divided", "moved"),
    lambda s: s.replace("two vessels of 180 μl each", "unfamiliar vessels"),
    lambda s: s.replace("were added", "were measured"),
    lambda s: s.replace("the respective vessels", "the vessels"),
    lambda s: s.replace("the respective vessels", "the respective wells"),
    lambda s: s.replace("3.2 μM enzyme A", "unusually low 3.2 μM enzyme A"),
])
def test_unknown_allocation_or_uncompleted_addition_stays_rejected(modification, native):
    text = modification(ALLOCATION)
    for token in ("3.2", "4.6"):
        with pytest.raises(ExperimentalContractError, match="interval_source_number"):
            scalar(text, token, native=native)


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("text", [
    ALLOCATION + " The vessels were incubated at 55 °C for 4.5 h.",
    ALLOCATION + " Duration and temperature were 55 °C and 4.5 h.",
    "The earlier concentration was between 3.2 and 4.6 μM. Later conditions were 55 °C and 4.5 h.",
])
def test_completed_sentences_do_not_veto_later_conditions(text, native):
    for token in ("55", "4.5"):
        assert scalar(text, token, native=native)["value"] == float(token)


@pytest.mark.parametrize("native", [False, True])
def test_inline_markup_retains_source_bytes_and_allocation_scope(native):
    text = "<p>Δ " + ALLOCATION.replace("two", "<i>two</i>").replace("3.2", "<strong>3.2</strong>") + "</p>"
    row = scalar(text, "3.2", native=native)
    witness = row["selector"]["witness"]
    assert text.encode()[witness["start"]:witness["end"]] == b"3.2"
    assert row["relation"] == "point"


@pytest.mark.parametrize("qualifier,bound,approximate", [("<", "lt", False), ("at most ", "le", False),
    ("approximately ", "point", True), ("&lt; about ", "lt", True), ("about >", "gt", True)])
def test_native_allocation_preserves_qualifiers_outside_numeric_only_witness(qualifier, bound, approximate):
    text = ALLOCATION.replace("3.2", qualifier + "3.2")
    row = scalar(text, "3.2", native=True)
    assert (row["relation"], row["approximate"]) == (bound, approximate)


def test_shared_allocation_retains_its_existing_approximation_and_lower_bound_rejections():
    for qualifier, error in [("approximately ", "approximate_source_number"), (">", "lower_bound_source_number")]:
        with pytest.raises(ExperimentalContractError, match=error):
            scalar(ALLOCATION.replace("3.2", qualifier + "3.2"), "3.2", native=False)
    text = ALLOCATION.replace("3.2", "<3.2").replace("4.6", "approximately 4.6")
    assert scalar(text, "3.2", native=False)["relation"] == "lt"
    with pytest.raises(ExperimentalContractError, match="approximate_source_number"):
        scalar(text, "4.6", native=False)


@pytest.mark.parametrize("expression,token,error", [("-3.2", "3.2", "partial_source_numeric_token"),
    ("3.2e2", "3.2", "partial_source_numeric_token"), ("3.2e309", "3.2e309", "numerical_model_range"),
    ("3.2e-4000", "3.2e-4000", "numerical_model_range"),
    ("3.2 × 10", "3.2", "source_arithmetic_expression"),
    ("3.2 ± 0.2", "0.2", "uncertainty_is_not_rate_point"),
    ("not greater than 3.2", "3.2", "negated_source_comparator")])
def test_native_other_guards_remain_independent_inside_allocation(expression, token, error):
    # Unrecognized list syntax may fail the conservative scope test first.
    with pytest.raises(ExperimentalContractError, match=error + "|interval_source_number"):
        scalar(ALLOCATION.replace("3.2", expression), token, native=True)
    with pytest.raises(ExperimentalContractError, match=error):
        scalar("Reported amount " + expression + " μM.", token, native=True)


def test_three_way_classifier_does_not_turn_unknown_source_words_into_operands():
    for text, token, expected in [(ALLOCATION, "3.2", "non_numeric_coordination"),
            (ALLOCATION.replace("two", "17"), "4.6", "non_numeric_coordination"),
            ("between approximately 3.2 and 4.6 μM", "4.6", "numeric_interval"),
            ("between unusually low 3.2 and 4.6 μM", "4.6", "unresolved")]:
        index = text.index(token)
        prefix, suffix = text[:index], text[index + len(token):]
        original = deepcopy((prefix, suffix))
        assert _between_numeric_scope(prefix, suffix) == expected
        assert (prefix, suffix) == original


def test_reserved_marker_collision_and_invalid_cardinal_are_unknown():
    for text in (ALLOCATION.replace("two", "one-one"),
            ALLOCATION.replace("3.2", "__selected_scalar__") + " and 3.2 μM"):
        index = text.index("4.6")
        assert _between_numeric_scope(text[:index], text[index + 3:]) == "unresolved"


@pytest.mark.parametrize("native", [False, True])
def test_signed_complete_scalar_is_not_clipped_by_scope_recognition(native):
    text = ALLOCATION.replace("3.2", "-3.2")
    assert scalar(text, "-3.2", native=native)["value"] == -3.2


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("encoded", ["&lt;between 2.1 and 2.9&gt;", "&lt;unfamiliar&gt;",
    '&lt;span style="between 2.1 and 2.9;"&gt;'])
def test_encoded_tag_looking_prose_cannot_authorize_coordination(encoded, native):
    text = ALLOCATION.replace("3.2", encoded + " 3.2")
    for token in ("3.2", "4.6"):
        with pytest.raises(ExperimentalContractError, match="interval_source_number|lower_bound_source_number"):
            scalar(text, token, native=native)


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("markup", ['<span style="color:red;">low</span>',
    '<em title="low; level.">low</em>', '<strong>low</strong>'])
def test_markup_attribute_punctuation_cannot_hide_unknown_range_endpoints(markup, native):
    text = ("The concentration was between an unusually " + markup
        + " concentration of 3.2 and 4.6 μM.")
    for token in ("3.2", "4.6"):
        with pytest.raises(ExperimentalContractError, match="interval_source_number"):
            scalar(text, token, native=native)


@pytest.mark.parametrize("native", [False, True])
def test_an_earlier_numeric_comparator_is_not_an_unclosed_markup_tag(native):
    text = "An earlier finding was <0.01.\n" + ALLOCATION
    for token in ("3.2", "4.6"):
        assert scalar(text, token, native=native)["relation"] == "point"
