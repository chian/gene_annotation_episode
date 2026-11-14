"""Read a finite reported relative-signal percentage from original JATS prose.

Literal presence and parsing establish neither the actual experimental subject
nor a calibrated molecule amount. The investigator owns those interpretations.
This reader acquires nothing and does not calculate experimental reliability.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

from .literature_experimental_contracts import ExperimentalContractError
from .literature_prose_reader import (
    _check_declarations, _direct_paragraph_text, _finite, _tag, _text,
)


VERSION = "relative_signal_extraction_v1"
_NUMBER = r"[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?"
_PERCENT = re.compile(
    rf"(?<![\w.,+−-])(?P<number>{_NUMBER})\s*%\s*\((?P<label>[^()]*)\)"
)
_LIMIT_PREFIX = re.compile(
    r"(?:<=|>=|[<>≤≥~≈±–—−-]|\b(?:(?:less|greater|more|fewer)\s+than|"
    r"at\s+most|at\s+least|up\s+to|below|above|approximately|about|circa|"
    r"roughly|around|between|from|not(?:\s+at)?))\s*$", re.IGNORECASE,
)
_RANGE_PREFIX = re.compile(
    rf"{_NUMBER}\s*%?\s*(?:to|and)\s*$", re.IGNORECASE,
)


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _contains_literal(text, literal):
    return re.search(r"(?<!\w)" + re.escape(literal) + r"(?!\w)", text) is not None


def _sentence_end(text, start):
    """Find finite prose punctuation, preserving decimal points in later ratios.

    This is deliberately not a general sentence parser. A period immediately
    before a digit belongs to a decimal token; other periods, ! and ? end this
    reader's comparison span. Abbreviations requiring inference are unsupported.
    """
    for position in range(start, len(text)):
        char = text[position]
        if char in "!?" or char == "." and not text[position + 1:position + 2].isdigit():
            return position
    return len(text)


def read_jats_relative_percent(source, *, section_id, paragraph_index,
                               expected_subject, variant, reference_literal):
    """Extract one ``NUMBER% (variant label) ... of REFERENCE`` comparison.

    ``paragraph_index`` is zero-based among the selected section's direct child
    p elements, not descendant/caption paragraphs. Inline markup remains text;
    embedded figures/tables do not. The comparison reference must follow the
    selected percentage in the same finite comparative sentence. Offsets index
    the retained paragraph TEXT in Unicode characters, not original XML bytes.
    No number or denominator magnitude is supplied by the caller.
    """
    if not isinstance(source, dict) or set(source) != {
            "source_ref", "artifact_ref", "xml", "representation"}:
        _fail("closed_fields_required", "source")
    for field in ("source_ref", "artifact_ref", "xml"):
        _text(source[field], "source." + field)
    if source["representation"] not in ("primary_jats", "synthetic_fixture"):
        _fail("unknown_source_representation", "source.representation")
    for name, value in (("section_id", section_id), ("expected_subject", expected_subject),
                        ("variant", variant), ("reference_literal", reference_literal)):
        _text(value, name)
    if type(paragraph_index) is not int or paragraph_index < 0:
        _fail("nonnegative_paragraph_index_required", "paragraph_index")
    _check_declarations(source["xml"])
    try:
        root = ET.fromstring(source["xml"])
    except (ET.ParseError, ValueError) as error:
        raise ExperimentalContractError("malformed_jats", "source.xml") from error
    if _tag(root) != "article":
        _fail("jats_article_required", "source.xml")
    sections = [element for element in root.iter() if element.get("id") == section_id]
    if len(sections) != 1 or _tag(sections[0]) != "sec":
        _fail("unique_section_required", "section_id")
    paragraphs = [element for element in sections[0] if _tag(element) == "p"]
    if paragraph_index >= len(paragraphs):
        _fail("direct_paragraph_unavailable", "paragraph_index")
    text = _direct_paragraph_text(paragraphs[paragraph_index])
    if not _contains_literal(text, expected_subject):
        _fail("subject_not_in_selected_prose", "expected_subject")
    reference_pattern = re.compile(r"(?<!\w)of\s+" + re.escape(reference_literal) + r"(?!\w)")
    candidates = []
    for match in _PERCENT.finditer(text):
        if not _contains_literal(match["label"], variant):
            continue
        before = text[:match.start()]
        if _LIMIT_PREFIX.search(before) or _RANGE_PREFIX.search(before):
            _fail("censored_or_approximate_percent", "value")
        # A limit stated after the parenthesis is equally not an exact point.
        following = text[match.end():_sentence_end(text, match.end())]
        if re.match(r"\s*(?:or\s+(?:less|more|greater|lower|higher)|at\s+(?:most|least))\b", following, re.IGNORECASE):
            _fail("censored_or_approximate_percent", "value")
        references = list(reference_pattern.finditer(following))
        first_of = re.search(r"(?<!\w)of\b", following)
        if references and first_of and first_of.start() != references[0].start():
            # A later denominator cannot overwrite an earlier, different one.
            continue
        if references and re.search(r"±|\+\s*/\s*[−-]|\b(?:SD|SEM|CI|confidence\s+interval)\b",
                                    following[:references[0].start()], re.IGNORECASE):
            _fail("relative_percent_uncertainty_unsupported", "uncertainty")
        if len(references) == 1:
            candidates.append(match)
        elif len(references) > 1:
            _fail("ambiguous_comparison_reference", "reference_literal")
    if not candidates:
        _fail("relative_percent_expression_unavailable", "variant")
    if len(candidates) != 1:
        _fail("ambiguous_relative_percent_expression", "variant")
    match = candidates[0]
    percent = _finite(match["number"], "value")
    if percent < 0:
        _fail("nonnegative_relative_percent_required", "value")
    ratio = percent / 100.0
    if not math.isfinite(ratio) or ratio == 0 and percent != 0:
        _fail("numerical_model_range", "value")
    observation = {"value": ratio,
        "origin": "synthetic" if source["representation"] == "synthetic_fixture" else "reported",
        "source": {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"],
            "representation": source["representation"], "section_id": section_id,
            "paragraph_index": paragraph_index, "paragraph_text": text,
            "expression": match.group(), "expression_start": match.start(),
            "expression_end": match.end()},
        "uncertainty": {"kind": "unreported", "magnitude": None, "count": None,
                        "sampling_basis": "unspecified"}}
    return {"version": VERSION, "subject": expected_subject, "variant": variant,
            "reference": reference_literal, "observations": [observation]}


__all__ = ["VERSION", "read_jats_relative_percent"]
