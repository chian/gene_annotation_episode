"""Synthetic literal syntax fixtures; no primary-source acquisition/validation."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_prose_reader import read_jats_quantity


PROSE = ("CsiD had a specific activity of 53+/− 3 µmol\u2009min<sup>−1</sup>\u2009mg<sup>−1</sup> "
         "and an apparent K<sub>m</sub> = 650+/− 20 µM for GA and "
         "K<sub>m</sub> = 100+/− 7 µM for αKG. "
         "<fig id='F'><caption><p id='CP'>SD, biological duplicates. "
         "Another specific activity of 999 ± 1 µmol/min/mg.</p></caption></fig>")


def source(prose=PROSE):
    return {"source_ref": "source:fixture", "artifact_ref": "artifact:fixture",
            "representation": "synthetic_fixture",
            "xml": f"<article><body><sec id='S'><p id='P'>{prose}</p></sec></body></article>"}


def read(value=None, **selection):
    return read_jats_quantity(value or source(), section_id=selection.pop("section_id", "S"),
        paragraph_id=selection.pop("paragraph_id", "P"),
        expected_subject=selection.pop("expected_subject", "CsiD"),
        quantity=selection.pop("quantity", "specific_activity"), **selection)


def test_specific_activity_literal_inline_units_and_exact_projection_proof():
    result = read()
    assert result["value"] == 53
    assert result["unit"] == "umol/min/mg"
    assert result["normalization"] == "mg_assayed_preparation"
    assert result["origin"] == "synthetic"
    assert result["uncertainty"] == {"kind": "unspecified", "magnitude": 3,
                                     "count": None, "sampling_basis": "unspecified"}
    proof = result["source"]
    assert proof["paragraph_text"][proof["expression_start"]:proof["expression_end"]] == proof["expression"]
    assert "999" not in proof["paragraph_text"]
    assert "biological duplicates" not in proof["paragraph_text"]
    assert "min−1" in proof["expression"]


@pytest.mark.parametrize("analyte,value,spread", [("GA", 650, 20), ("αKG", 100, 7)])
def test_distinct_km_analytes_remain_bound(analyte, value, spread):
    result = read(quantity="apparent_km", analyte=analyte)
    assert (result["value"], result["unit"], result["uncertainty"]["magnitude"]) == (value, "uM", spread)
    assert result["analyte"] == analyte
    assert result["normalization"] == "none"
    assert result["source"]["expression"].endswith("for " + analyte)


@pytest.mark.parametrize("expression,quantity,analyte,value,spread", [
    ("specific activity of 53000 ± 3000 nmol/min/mg", "specific_activity", None, 53, 3),
    ("specific activity of 53 ± 3 μmol min⁻¹ mg⁻¹", "specific_activity", None, 53, 3),
    ("specific activity of -2.3e-2 ± 1e-3 umol/min/mg", "specific_activity", None, -.023, .001),
    ("Km = .65 ± .02 mM for GA", "apparent_km", "GA", 650, 20),
    ("Km = 650000 ± 20000 nM for GA", "apparent_km", "GA", 650, 20),
    ("specific activity of 53 umol/min/mg", "specific_activity", None, 53, None),
    ("Km = 650 uM for GA", "apparent_km", "GA", 650, None),
])
def test_supported_units_signs_and_unreported_spread(expression, quantity, analyte, value, spread):
    result = read(source("CsiD " + expression + "."), quantity=quantity, analyte=analyte)
    assert result["value"] == pytest.approx(value)
    assert result["uncertainty"]["magnitude"] == spread
    assert result["uncertainty"]["kind"] == ("unspecified" if spread is not None else "unreported")


def test_reported_source_not_relabeled_synthetic_and_input_unchanged():
    value = source()
    value["representation"] = "primary_jats"
    original = deepcopy(value)
    assert read(value)["origin"] == "reported"
    assert value == original


@pytest.mark.parametrize("selection,code", [
    ({"section_id": "missing"}, "unique_section_required"),
    ({"paragraph_id": "missing"}, "unique_paragraph_required"),
    ({"paragraph_id": "CP"}, "paragraph_not_direct_prose"),
    ({"expected_subject": "Csi"}, "subject_not_in_selected_prose"),
    ({"expected_subject": "Another"}, "subject_not_in_selected_prose"),
    ({"quantity": "apparent_km"}, "nonempty_source_token_required"),
    ({"quantity": "apparent_km", "analyte": "G"}, "quantity_expression_unavailable"),
    ({"quantity": "Kd"}, "unsupported_quantity"),
    ({"analyte": "GA"}, "analyte_only_for_km"),
])
def test_selection_failures_are_explicit(selection, code):
    with pytest.raises(ExperimentalContractError) as error:
        read(**selection)
    assert error.value.code == code
    assert error.value.field


@pytest.mark.parametrize("prose,code", [
    ("CsiD specific activity of 1 ± 2 umol/min/mg; specific activity of 3 ± 4 umol/min/mg", "ambiguous_quantity_expression"),
    ("CsiD specific activity of >53 ± 3 umol/min/mg", "quantity_expression_unavailable"),
    ("CsiD specific activity of 53 to 56 umol/min/mg", "quantity_expression_unavailable"),
    ("CsiD specific activity of NaN ± 3 umol/min/mg", "quantity_expression_unavailable"),
    ("CsiD specific activity of 53 ± -3 umol/min/mg", "negative_uncertainty"),
    ("CsiD specific activity of 1e999 ± 3 umol/min/mg", "finite_number_required"),
    ("CsiD specific activity of 1e-999 ± 3 umol/min/mg", "numerical_model_range"),
    ("CsiD specific activity of 1e-323 ± 3 nmol/min/mg", "numerical_model_range"),
    ("CsiD specific activity of 53 ± 1e-323 nmol/min/mg", "numerical_model_range"),
    ("CsiD specific activity of 53 ± 3 µmol/min", "quantity_expression_unavailable"),
    ("CsiD specific activity of 53 ± 3 µmol/min/mg/s", "quantity_expression_unavailable"),
])
def test_unsupported_conflicting_and_numerically_invalid_expressions(prose, code):
    with pytest.raises(ExperimentalContractError) as error:
        read(source(prose))
    assert error.value.code == code


@pytest.mark.parametrize("expression", ["Km = 0 uM for GA", "Km = -1 uM for GA"])
def test_nonpositive_km_rejected(expression):
    with pytest.raises(ExperimentalContractError, match="positive_km_required"):
        read(source("CsiD " + expression), quantity="apparent_km", analyte="GA")


def test_namespace_qualified_jats():
    value = source()
    value["xml"] = value["xml"].replace("<article>", "<article xmlns='urn:jats'>")
    assert read(value)["value"] == 53


@pytest.mark.parametrize("mutation,code", [
    (lambda xml: xml.replace("</body>", "<sec id='S'/></body>"), "unique_section_required"),
    (lambda xml: xml.replace("</body>", "<p id='S'>other</p></body>"), "unique_section_required"),
    (lambda xml: xml.replace("</body>", "<p id='P'>other</p></body>"), "unique_paragraph_required"),
    (lambda xml: xml.replace("<p id='P'>", "<sec id='child'><p id='P'>").replace("</p></sec>", "</p></sec></sec>"), "paragraph_not_direct_prose"),
    (lambda xml: xml.replace("<sec id='S'>", "<sec id='S'/><sec id='T'>"), "paragraph_outside_section"),
    (lambda xml: xml[:-4], "malformed_jats"),
    (lambda xml: xml.replace("article", "root"), "jats_article_required"),
    (lambda xml: '<!DOCTYPE article [<!ENTITY x "value">]>' + xml, "xml_declarations_not_supported"),
])
def test_jats_structure_and_security_failures(mutation, code):
    value = source()
    value["xml"] = mutation(value["xml"])
    with pytest.raises(ExperimentalContractError) as error:
        read(value)
    assert error.value.code == code


@pytest.mark.parametrize("field,new,code", [
    ("source_ref", "", "nonempty_source_token_required"),
    ("xml", b"<article/>", "nonempty_source_token_required"),
    ("representation", "retained_summary", "unknown_source_representation"),
])
def test_invalid_source_contract(field, new, code):
    value = source()
    value[field] = new
    with pytest.raises(ExperimentalContractError) as error:
        read(value)
    assert error.value.code == code


def test_rejects_extra_fields_including_model_supplied_numbers():
    value = source()
    value["value"] = 53
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        read(value)


@pytest.mark.parametrize("declaration", [
    '<!DOCTYPE article\n PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD with MathML3 v1.4 20241031//EN" "JATS-archivearticle1-4-mathml3.dtd">',
    '<!DOCTYPE article SYSTEM "https://invalid.example/not-loaded.dtd">',
    "<!DOCTYPE article SYSTEM 'file:///nonexistent/not-loaded.dtd'>",
])
def test_external_article_doctype_is_inert_and_original_source_unchanged(declaration):
    value = source()
    value["xml"] = declaration + value["xml"]
    before = deepcopy(value)
    # No source or external DTD file/network access is permitted. The actual
    # ElementTree parser receives the original XML, including its declaration.
    with patch("builtins.open", side_effect=AssertionError("unexpected open")), \
            patch("io.open", side_effect=AssertionError("unexpected io.open")), \
            patch("urllib.request.urlopen", side_effect=AssertionError("unexpected urlopen")), \
            patch("socket.create_connection", side_effect=AssertionError("unexpected connection")):
        result = read(value)
    assert result["value"] == 53
    assert value == before


@pytest.mark.parametrize("declaration", [
    '<!DOCTYPE article SYSTEM "unused.dtd" [<!ENTITY x "53">]>',
    '<!DOCTYPE article SYSTEM "unused.dtd" []>',
    '<!DOCTYPE article SYSTEM "unused.dtd">\n<!DOCTYPE article SYSTEM "unused2.dtd">',
    '<!DOCTYPE article PUBLIC "unclosed identifier>',
    '<!DOCTYPE article PUBLIC "only one identifier">',
    '<!DOCTYPE other SYSTEM "unused.dtd">',
    '<!DOCTYPE article>',
    '<!doctype article SYSTEM "unused.dtd">',
])
def test_internal_malformed_and_duplicate_dtds_remain_rejected(declaration):
    value = source()
    value["xml"] = declaration + value["xml"]
    with pytest.raises(ExperimentalContractError, match="xml_declarations_not_supported"):
        read(value)


def test_external_entity_reference_is_not_resolved():
    value = source("CsiD specific activity of &external; ± 3 umol/min/mg")
    value["xml"] = '<!DOCTYPE article SYSTEM "file:///nonexistent/entity.dtd">' + value["xml"]
    with patch("builtins.open", side_effect=AssertionError("unexpected open")), \
            pytest.raises(ExperimentalContractError, match="xml_entity_reference_not_supported"):
        read(value)


def test_standard_xml_character_escapes_remain_usable():
    result = read(source("CsiD &amp; another molecule: specific activity of 53 ± 3 umol/min/mg"))
    assert "CsiD & another" in result["source"]["paragraph_text"]
