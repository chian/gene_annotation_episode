"""Synthetic HTML fixtures only; no source-paper/network acquisition."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_html_quantity_reader import VERSION, read_html_quantity
from gene_annotation_episode.literature_prose_reader import read_jats_quantity

PROSE = ("The K<sub>m</sub> of the transporter BtsT for pyruvate measured in "
         "intact cells was 16.5 ± 6.4 μM.")


def source(prose=PROSE, *, wrapper=None):
    body = wrapper if wrapper is not None else f'<section id="S"><p id="P">{prose}</p></section>'
    return {"source_ref": "source:fixture", "artifact_ref": "artifact:fixture",
            "representation": "synthetic_fixture", "html": f'<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>{body}</body></html>'}


def read(value=None, **selection):
    options = dict(section_id="S", paragraph_id="P", expected_subject="BtsT",
                   quantity="apparent_km", analyte="pyruvate")
    options.update(selection)
    return read_html_quantity(source() if value is None else value, **options)


def test_natural_inline_original_html_exact_projection_and_untyped_spread():
    original = source()
    before = deepcopy(original)
    result = read(original)
    assert result["version"] == VERSION == "a105_html_quantity_v1"
    assert result["value"] == 16.5
    assert result["unit"] == "uM"
    assert result["normalization"] == "none"
    assert result["origin"] == "synthetic"
    assert result["uncertainty"] == {"kind": "unspecified", "magnitude": 6.4,
                                     "count": None, "sampling_basis": "unspecified"}
    proof = result["source"]
    assert proof["paragraph_text"] == PROSE.replace("<sub>", "").replace("</sub>", "")
    assert proof["paragraph_text"][proof["expression_start"]:proof["expression_end"]] == proof["expression"]
    assert proof["section_id"] == "S" and proof["paragraph_id"] == "P"
    assert original == before


def test_exact_output_keys_match_jats_contract():
    html = read(source("BtsT apparent Km = 16.5 ± 6.4 μM for pyruvate."))
    jats = read_jats_quantity({"source_ref": "source:fixture", "artifact_ref": "artifact:fixture",
        "xml": '<article><sec id="S"><p id="P">BtsT apparent Km = 16.5 ± 6.4 μM for pyruvate.</p></sec></article>',
        "representation": "synthetic_fixture"}, section_id="S", paragraph_id="P",
        expected_subject="BtsT", quantity="apparent_km", analyte="pyruvate")
    assert set(html) == set(jats)
    assert set(html["source"]) == set(jats["source"])
    for key in set(html) - {"version", "source"}:
        assert html[key] == jats[key]


@pytest.mark.parametrize("expression,value,spread", [
    ("Km = .0165 ± .0064 mM for pyruvate", 16.5, 6.4),
    ("Km = 16500 +/− 6400 nM for pyruvate", 16.5, 6.4),
    ("K<sub>m</sub> = 1.65e1 μM for pyruvate", 16.5, None),
    ("apparent Km = +16.5 ± 0 uM for pyruvate", 16.5, 0),
])
def test_finite_native_units_signs_and_unreported(expression, value, spread):
    result = read(source("BtsT " + expression + "."))
    assert result["value"] == pytest.approx(value)
    assert result["uncertainty"]["magnitude"] == pytest.approx(spread) if spread is not None else result["uncertainty"]["magnitude"] is None
    assert result["uncertainty"]["kind"] == ("unreported" if spread is None else "unspecified")


def test_no_attribution_or_uncertainty_borrowing():
    value = source("BtsT is mentioned. Another transporter: Km = 16.5 ± 6.4 μM for pyruvate. "
                   "SEM, n=3, biological replicates.")
    result = read(value)
    assert result["uncertainty"] == {"kind": "unspecified", "magnitude": 6.4,
                                     "count": None, "sampling_basis": "unspecified"}
    # This function establishes token presence; the parent owns attribution.
    assert result["subject"] == "BtsT"


def test_descriptive_km_mention_is_not_another_measurement():
    prose = "In order to determine the Km for pyruvate uptake, we measured uptake. " + PROSE
    result = read(source(prose))
    assert result["value"] == 16.5
    assert result["source"]["paragraph_text"].startswith("In order to determine the Km")


def test_explicit_foreign_svg_empty_elements_are_parsed_but_not_read():
    value = source(PROSE + '<span><svg xmlns="http://www.w3.org/2000/svg">'
        '<path d="M0 0"/><text>Km = 999 μM for pyruvate</text><use href="#icon"/>'
        '</svg></span><svg/>')
    result = read(value)
    assert result["value"] == 16.5
    assert "999" not in result["source"]["paragraph_text"]


@pytest.mark.parametrize("attribute", ['hidden', 'aria-hidden="true"', 'style="display: none !important"',
    'style="visibility:hidden"', 'style="content-visibility: hidden"', 'class="visually-hidden"', 'inert'])
def test_hidden_nodes_cannot_supply_numbers_subject_or_uncertainty(attribute):
    value = source(f'BtsT Km = 16.5 μM for pyruvate.<span {attribute}> Km = 999 ± 1 μM for pyruvate. SEM</span>')
    result = read(value)
    assert result["value"] == 16.5 and result["uncertainty"]["magnitude"] is None
    assert "999" not in result["source"]["paragraph_text"]
    with pytest.raises(ExperimentalContractError, match="subject_not_in_selected_prose"):
        read(source(f'<span {attribute}>BtsT</span> Km = 16.5 μM for pyruvate.'))


def test_script_style_caption_figure_table_text_never_supplies_evidence():
    body = (f'<section id="S"><p id="P">{PROSE}</p>'
            '<figure id="F"><figcaption><p id="C">Km = 999 μM for pyruvate. SEM n=8</p></figcaption></figure>'
            '<table><tbody><tr><td><p id="T">Km = 999 μM for pyruvate.</p></td></tr></tbody></table>'
            '<script>if (1 < 3) { text = "Km = 999 μM for pyruvate."; }</script>'
            '<style>.x {display:none}</style></section>')
    result = read(source(wrapper=body))
    assert "999" not in result["source"]["paragraph_text"]
    for paragraph in ("C", "T"):
        with pytest.raises(ExperimentalContractError, match="paragraph_not_direct_prose"):
            read(source(wrapper=body), paragraph_id=paragraph)


@pytest.mark.parametrize("wrapper", [
    '<section id="S"><section id="child"><p id="P">{prose}</p></section></section>',
    '<section id="S"><div class="section"><p id="P">{prose}</p></div></section>',
    '<section id="S"><div class="caption"><p id="P">{prose}</p></div></section>',
    '<div hidden><section id="S"><p id="P">{prose}</p></section></div>',
    '<section id="S"><p id="P" aria-hidden="true">{prose}</p></section>',
])
def test_selected_paragraph_nested_excluded_or_hidden_rejected(wrapper):
    with pytest.raises(ExperimentalContractError, match="paragraph_not_direct_prose"):
        read(source(wrapper=wrapper.format(prose=PROSE)))


def test_direct_paragraph_selector_original_order_excludes_figures_children_and_hidden():
    body = ('<section id="S"><p>Inhibitors.</p><figure><figcaption><p>Figure text</p></figcaption></figure>'
            f'<p>{PROSE}</p><section id="child"><p>Nested</p></section>'
            '<p hidden>Hidden</p></section>')
    result = read(source(wrapper=body), paragraph_id="direct_paragraph:1")
    assert result["value"] == 16.5
    assert result["source"]["paragraph_id"] == "direct_paragraph:1"
    with pytest.raises(ExperimentalContractError, match="unique_paragraph_required"):
        read(source(wrapper=body), paragraph_id="direct_paragraph:2")
    with pytest.raises(ExperimentalContractError, match="quantity_expression_unavailable"):
        read(source(wrapper=body), paragraph_id="direct_paragraph:0", expected_subject="Inhibitors", analyte="Inhibitors")


@pytest.mark.parametrize("selector", ["direct_paragraph:-1", "direct_paragraph:01", "direct_paragraph:1.0", "direct_paragraph:"])
def test_invalid_direct_selector(selector):
    with pytest.raises(ExperimentalContractError, match="invalid_paragraph_selector"):
        read(paragraph_id=selector)


def test_extremely_large_direct_selector_is_structured_unavailable():
    with pytest.raises(ExperimentalContractError, match="unique_paragraph_required"):
        read(paragraph_id="direct_paragraph:" + "9" * 5000)


@pytest.mark.parametrize("body,code", [
    ('<section id="S"><p id="P">{prose}</p></section><section id="S"></section>', "unique_section_required"),
    ('<section id="S"><p id="P">{prose}</p></section><p id="P">Other</p>', "unique_paragraph_required"),
    ('<section id="S"><p id="P">{prose}</p></section><i id="x"></i><b id="x"></b>', "duplicate_html_id"),
    ('<section id="S"></section><p id="P">{prose}</p>', "paragraph_outside_section"),
    ('<section id="S"></section><section id="T"><p id="P">{prose}</p></section>', "paragraph_outside_section"),
    ('<p id="S">Other</p><p id="P">{prose}</p>', "unique_section_required"),
    ('<section id="S"><span id="P">{prose}</span></section>', "unique_paragraph_required"),
])
def test_global_ids_and_real_containment(body, code):
    with pytest.raises(ExperimentalContractError, match=code):
        read(source(wrapper=body.format(prose=PROSE)))


@pytest.mark.parametrize("body", [
    '<section id="S"><p id="P">{prose}</section></p>',
    '<section id="S"><p id="P">{prose}</p>',
    '<section id="S"><p id="P">{prose}<p>Other</p></section>',
    '<section id="S"><p id="P">{prose}<figure>Caption</figure></p></section>',
    '<section id="S"><p id="P" id="Other">{prose}</p></section>',
    '<section id="S"><p id="P">{prose}<span/></p></section>',
])
def test_malformed_markup_is_not_repaired(body):
    with pytest.raises(ExperimentalContractError) as error:
        read(source(wrapper=body.format(prose=PROSE)))
    assert error.value.code in {"malformed_html", "duplicate_html_attribute"}


@pytest.mark.parametrize("suffix", ["<broken", '<broken foo="bad', "<!broken>",
    "<!-- incomplete", "<div></div garbage>", "<p>Closed</p><", '<span title=abc"def></span>'])
def test_malformed_markup_after_valid_selected_paragraph_is_still_rejected(suffix):
    with pytest.raises(ExperimentalContractError, match="malformed_html"):
        read(source(wrapper=f'<section id="S"><p id="P">{PROSE}</p></section>' + suffix))


@pytest.mark.parametrize("expression,code", [
    ("Km = <span>1</span><span>6.5</span> μM for pyruvate", "quantity_expression_unavailable"),
    ("Km = <span>16</span><span>.5</span> μM for pyruvate", "quantity_expression_unavailable"),
    ("Km = 16.5 μM<sup>2</sup> for pyruvate", "quantity_expression_unavailable"),
    ("Km = >16.5 μM for pyruvate", "quantity_expression_unavailable"),
    ("Km = ≤16.5 μM for pyruvate", "quantity_expression_unavailable"),
    ("Km = 10–20 μM for pyruvate", "quantity_expression_unavailable"),
    ("Km = 10 to 20 μM for pyruvate", "quantity_expression_unavailable"),
    ("Km = 10 μM/min for pyruvate", "quantity_expression_unavailable"),
    ("Km = 10 μM-1 for pyruvate", "quantity_expression_unavailable"),
    ("Km = 16.5 UM for pyruvate", "quantity_expression_unavailable"),
    ("Km = NaN μM for pyruvate", "quantity_expression_unavailable"),
    ("Km = inf μM for pyruvate", "quantity_expression_unavailable"),
    ("Km = 1e999 μM for pyruvate", "finite_number_required"),
    ("Km = 1e-999 μM for pyruvate", "numerical_model_range"),
    ("Km = 1e-323 nM for pyruvate", "numerical_model_range"),
    ("Km = 1e308 mM for pyruvate", "numerical_model_range"),
    ("Km = 16.5 ± -6.4 μM for pyruvate", "negative_uncertainty"),
    ("Km = 16.5 ± 1e-999 μM for pyruvate", "numerical_model_range"),
    ("Km = 16.5 ± 1e-323 nM for pyruvate", "numerical_model_range"),
    ("Km = 0 μM for pyruvate", "positive_km_required"),
    ("Km = -1 μM for pyruvate", "positive_km_required"),
    ("Km = 1 μM for pyruvate. Km = 2 μM for pyruvate", "ambiguous_quantity_expression"),
    ("Km = 1 μM for pyruvate. Km = 2 μM for lactate", "ambiguous_quantity_expression"),
    ("Km > 1 μM for pyruvate. Km = 2 μM for pyruvate", "ambiguous_quantity_expression"),
])
def test_unsafe_unsupported_ambiguous_or_numerically_invalid(expression, code):
    with pytest.raises(ExperimentalContractError, match=code):
        read(source("BtsT " + expression + "."))


@pytest.mark.parametrize("tail", ["10 to 20 μM.", ">10 μM.", "10 μM to 20 μM.", "10 μM−1."])
def test_natural_prose_censoring_and_ranges_rejected(tail):
    prose = "The Km of the transporter BtsT for pyruvate measured in intact cells was " + tail
    with pytest.raises(ExperimentalContractError, match="quantity_expression_unavailable"):
        read(source(prose))


@pytest.mark.parametrize("selection,code", [
    ({"expected_subject": "Bts"}, "subject_not_in_selected_prose"),
    ({"analyte": "pyru"}, "analyte_not_in_selected_prose"),
    ({"analyte": None}, "nonempty_source_token_required"),
    ({"quantity": "specific_activity"}, "unsupported_quantity"),
    ({"quantity": "turnover_rate"}, "unsupported_quantity"),
    ({"section_id": "missing"}, "unique_section_required"),
    ({"paragraph_id": "missing"}, "unique_paragraph_required"),
])
def test_contract_and_selection_failures(selection, code):
    with pytest.raises(ExperimentalContractError, match=code):
        read(**selection)


def test_source_closed_fields_and_representation():
    value = source()
    value["value"] = 16.5
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        read(value)
    value = source()
    value["representation"] = "primary_jats"
    with pytest.raises(ExperimentalContractError, match="unknown_source_representation"):
        read(value)
    value = source()
    value["html"] = b"<section/>"
    with pytest.raises(ExperimentalContractError, match="nonempty_source_token_required"):
        read(value)


def test_html_entities_void_elements_comments_and_reported_origin_without_io():
    value = source(PROSE.replace("±", "&plusmn;").replace("μM", "&micro;M") + '<br/> &amp; other.')
    value["representation"] = "primary_html"
    before = deepcopy(value)
    with patch("builtins.open", side_effect=AssertionError("unexpected file access")), \
            patch("socket.create_connection", side_effect=AssertionError("unexpected network")), \
            patch("urllib.request.urlopen", side_effect=AssertionError("unexpected acquisition")):
        result = read(value)
    assert result["origin"] == "reported"
    assert result["value"] == 16.5 and value == before


@pytest.mark.parametrize("decl", ['<!DOCTYPE html [<!ENTITY x "value">]>',
    '<!DOCTYPE article>', '<!DOCTYPE html><!DOCTYPE html>', '<?xml version="1.0"?>'])
def test_declarations_do_not_load_entities_or_get_repaired(decl):
    value = source()
    value["html"] = value["html"].replace("<!DOCTYPE html>", decl)
    with pytest.raises(ExperimentalContractError, match="html_declarations_not_supported"):
        read(value)
