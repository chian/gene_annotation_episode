"""Read selected literal JATS activity/Km expressions without inventing evidence.

This finite reader performs no acquisition or scientific subject attribution.
The caller selects a paragraph and interprets its experimental relationship.
Subject validation establishes literal presence only. Nested figures/tables are
excluded so that their captions cannot supply uncertainty for the prose assay.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a105_jats_quantity_v1"
_NUMBER = r"[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?"
_SPREAD = rf"(?:\s*(?:\+\s*/\s*[−-]|±)\s*(?P<spread>{_NUMBER}))?"
_ACTIVITY_UNIT = (
    r"(?:[µμu]mol|nmol)\s*(?:/\s*min\s*/\s*mg|"
    r"min\s*(?:[−-]1|⁻¹)\s*mg\s*(?:[−-]1|⁻¹))"
)
_CONCENTRATION_UNIT = r"(?:[µμu]M|nM|mM)"
_ACTIVITY = re.compile(
    rf"(?<!\w)specific\s+activity\s+of\s+(?P<value>{_NUMBER})"
    rf"{_SPREAD}\s*(?P<unit>{_ACTIVITY_UNIT})(?![\w/⁻^−-])", re.IGNORECASE,
)
# Preserve unit case: mM and uM are distinct, as are mol and M.
_KM_PREFIX = rf"(?<!\w)(?:apparent\s+)?K\s*_?\s*m\s*=\s*(?P<value>{_NUMBER})"
_EXCLUDED = {"fig", "fig-group", "table-wrap", "table-wrap-group", "table", "caption"}
_DTD_LITERAL = r'''(?:"[^"<>\[\]]*"|'[^'<>\[\]]*')'''
_EXTERNAL_ARTICLE_DTD = re.compile(
    rf"<!DOCTYPE\s+article\s+(?:PUBLIC\s+{_DTD_LITERAL}\s+{_DTD_LITERAL}"
    rf"|SYSTEM\s+{_DTD_LITERAL})\s*>"
)


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


def _tag(element):
    return element.tag.rsplit("}", 1)[-1]


def _check_declarations(xml):
    """Allow an inert external article DTD; reject custom entity machinery.

    ElementTree does not load an external DTD. Pass the untouched XML through
    after checking the declaration's finite syntax; do not fetch or strip it.
    Internal subsets and entity declarations remain unsupported. Standard XML
    character escapes (amp/lt/gt/apos/quot and numeric references) remain valid.
    """
    if re.search(r"<!\s*ENTITY\b", xml, re.IGNORECASE):
        _fail("xml_declarations_not_supported", "source.xml")
    starts = list(re.finditer(r"<!\s*DOCTYPE\b", xml, re.IGNORECASE))
    if len(starts) > 1 or starts and not _EXTERNAL_ARTICLE_DTD.match(xml, starts[0].start()):
        _fail("xml_declarations_not_supported", "source.xml")
    if any(name not in {"amp", "lt", "gt", "apos", "quot"}
           for name in re.findall(r"&([A-Za-z_:][\w.:-]*);", xml)):
        _fail("xml_entity_reference_not_supported", "source.xml")


def _direct_paragraph_text(element):
    """Inline markup remains text; embedded figure/table content does not."""
    parts = [element.text or ""]
    for child in element:
        if _tag(child) not in _EXCLUDED:
            parts.append(_direct_paragraph_text(child))
        parts.append(child.tail or "")
    return "".join(parts)


def _finite(token, field):
    try:
        value = float(token.replace("−", "-"))
    except (OverflowError, ValueError):
        _fail("finite_number_required", field)
    if not math.isfinite(value):
        _fail("finite_number_required", field)
    # Underflow to zero must not silently turn a reported nonzero into zero.
    mantissa = token.lower().split("e", 1)[0]
    if value == 0 and any(character in "123456789" for character in mantissa):
        _fail("numerical_model_range", field)
    return value


def _unit(raw, quantity):
    compact = re.sub(r"\s+", "", raw).replace("µ", "u").replace("μ", "u")
    if quantity == "apparent_km":
        scales = {"uM": 1.0, "nM": 0.001, "mM": 1000.0}
        if compact not in scales:
            _fail("unsupported_concentration_unit", "unit")
        return "uM", scales[compact]
    compact = compact.replace("⁻¹", "-1").replace("−", "-")
    scales = {"umol/min/mg": 1.0, "nmol/min/mg": 0.001,
              "umolmin-1mg-1": 1.0, "nmolmin-1mg-1": 0.001}
    if compact not in scales:
        _fail("unsupported_specific_activity_unit", "unit")
    return "umol/min/mg", scales[compact]


def read_jats_quantity(source, *, section_id, paragraph_id, expected_subject,
                       quantity, analyte=None):
    """Extract one unambiguous reported point and optional untyped ± spread.

    Supported syntax: ``specific activity of NUMBER [± NUMBER] UNIT`` or
    ``[apparent] Km = NUMBER [± NUMBER] CONCENTRATION for ANALYTE``. XML inline
    subscripts/superscripts are flattened. Censoring, ranges, graphs and missing
    units are outside this reader. All offsets index retained paragraph TEXT in
    Unicode characters, not original XML bytes; the XML artifact and selectors
    remain the original source locators. No caller-supplied number is accepted.
    """
    if not isinstance(source, dict) or set(source) != {
            "source_ref", "artifact_ref", "xml", "representation"}:
        _fail("closed_fields_required", "source")
    for field in ("source_ref", "artifact_ref", "xml"):
        _text(source[field], "source." + field)
    if source["representation"] not in ("primary_jats", "synthetic_fixture"):
        _fail("unknown_source_representation", "source.representation")
    for field, value in (("section_id", section_id), ("paragraph_id", paragraph_id),
                         ("expected_subject", expected_subject)):
        _text(value, field)
    if quantity not in ("specific_activity", "apparent_km"):
        _fail("unsupported_quantity", "quantity")
    if quantity == "apparent_km":
        _text(analyte, "analyte")
    elif analyte is not None:
        _fail("analyte_only_for_km", "analyte")
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
    # Select IDs globally first, so duplicate IDs elsewhere cannot redirect a
    # seemingly valid scoped request to one arbitrary occurrence.
    paragraphs = [element for element in root.iter()
                  if element.get("id") == paragraph_id]
    if len(paragraphs) != 1 or _tag(paragraphs[0]) != "p":
        _fail("unique_paragraph_required", "paragraph_id")
    paragraph = paragraphs[0]
    if paragraph not in list(sections[0].iter()):
        _fail("paragraph_outside_section", "paragraph_id")
    # A caption paragraph is not direct scientific prose even when scoped under
    # the selected section. Likewise do not reach through a child section.
    parents = {child: parent for parent in root.iter() for child in parent}
    ancestor = parents.get(paragraph)
    while ancestor is not None and ancestor is not sections[0]:
        if _tag(ancestor) in _EXCLUDED or _tag(ancestor) == "sec":
            _fail("paragraph_not_direct_prose", "paragraph_id")
        ancestor = parents.get(ancestor)
    text = _direct_paragraph_text(paragraph)
    if not re.search(r"(?<!\w)" + re.escape(expected_subject) + r"(?!\w)", text):
        _fail("subject_not_in_selected_prose", "expected_subject")
    if quantity == "specific_activity":
        matches = list(_ACTIVITY.finditer(text))
    else:
        pattern = re.compile(
            rf"{_KM_PREFIX}{_SPREAD}\s*(?P<unit>{_CONCENTRATION_UNIT})(?!\w)"
            rf"\s+for\s+{re.escape(analyte)}(?!\w)"
        )
        matches = list(pattern.finditer(text))
    if not matches:
        _fail("quantity_expression_unavailable", "quantity")
    if len(matches) != 1:
        _fail("ambiguous_quantity_expression", "quantity")
    match = matches[0]
    value = _finite(match["value"], "value")
    spread = _finite(match["spread"], "uncertainty.magnitude") if match["spread"] else None
    if quantity == "apparent_km" and value <= 0:
        _fail("positive_km_required", "value")
    if spread is not None and spread < 0:
        _fail("negative_uncertainty", "uncertainty.magnitude")
    unit, scale = _unit(match["unit"], quantity)
    value *= scale
    spread = spread * scale if spread is not None else None
    if not math.isfinite(value) or spread is not None and not math.isfinite(spread):
        _fail("numerical_model_range", "unit_conversion")
    if value == 0 and _finite(match["value"], "value") != 0:
        _fail("numerical_model_range", "unit_conversion")
    if spread == 0 and _finite(match["spread"], "uncertainty.magnitude") != 0:
        _fail("numerical_model_range", "unit_conversion")
    return {"version": VERSION, "subject": expected_subject, "quantity": quantity,
        "analyte": analyte, "value": value, "unit": unit,
        "uncertainty": {"kind": "unspecified" if spread is not None else "unreported",
                        "magnitude": spread, "count": None, "sampling_basis": "unspecified"},
        "origin": "synthetic" if source["representation"] == "synthetic_fixture" else "reported",
        "normalization": "mg_assayed_preparation" if quantity == "specific_activity" else "none",
        "source": {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"],
            "representation": source["representation"], "section_id": section_id,
            "paragraph_id": paragraph_id, "paragraph_text": text,
            "expression": match.group(), "expression_start": match.start(),
            "expression_end": match.end()}}


__all__ = ["VERSION", "read_jats_quantity"]
