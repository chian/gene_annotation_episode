"""Independent source custody/arithmetic and existing amount-reader execution.

This is a review artifact, not a new grader, source acquisition or episode run.
All output is exclusive to this directory; the frozen research packet is read-only.
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import time
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from gene_annotation_episode.literature_amount_inputs import LITERAL_FIELDS, read_amount_inputs
from gene_annotation_episode.literature_amount_calculations import populate_amount_components


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / "research/experimental_scoring_review_2026-10-23/a105_effect_isolation_case_234"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    with (OUT / name).open("x") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def main():
    manifest = json.loads((PACKET / "MANIFEST_001.json").read_text())
    for row in manifest["files"]:
        data = (PACKET / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and digest(data) == row["sha256"], row["path"]

    ledger = json.loads((PACKET / "SOURCE_WITNESSES_003.json").read_text())
    spans = []
    for row in ledger["witnesses"]:
        if "start" not in row:
            continue
        data = (PACKET / row["artifact"]).read_bytes()
        assert digest(data) == row["artifact_sha256"]
        assert data[row["start"]:row["end"]] == row["literal"].encode()
        spans.append(row["id"])

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(PACKET / "originals/mmc1.docx") as archive:
        document = archive.read("word/document.xml")
        assert document == (PACKET / "originals/word_document.xml").read_bytes()
        for name in ("image2.emf", "image5.emf", "image6.emf", "image7.png", "image8.png"):
            assert archive.read("word/media/" + name) == (PACKET / "originals/media" / name).read_bytes()
    paragraphs = ["".join(t.text or "" for t in p.iter("{" + ns["w"] + "}t"))
                  for p in ET.fromstring(document).iter("{" + ns["w"] + "}p")]
    # The retained locator convention uses zero-based Word paragraph indices.
    assert paragraphs[130] == "WP_164930753.1"
    assert paragraphs[112] == "WP_010881296.1"
    assert paragraphs[311].startswith("Figure S7:")
    assert "room temperature" in paragraphs[289]
    assert "18 hours" in paragraphs[299]

    expected = {
        "reported_equilibrium_fraction_sum": Fraction(397 + 603, 1000),
        "reported_equilibrium_R5P_Ru5P_ratio": Fraction(603, 397),
        "printed_S5_integral_R5P_fraction": Fraction(152, 100 + 152),
        "nominal_HFP_bulk_mass_ratio_approximate": Fraction(5, 7),
        "nominal_bulk_HFP_denominator_multiplier_approximate": Fraction(7, 5),
        "other_preparations_positive_fraction_finite_cohort": Fraction(4, 5),
        "RpiA_covered_residue_fraction": Fraction(101, 219),
        "HFP_covered_residue_fraction": Fraction(161, 203),
        "main_text_time_bound_division_only": Fraction(18 * 60, 10),
    }
    arithmetic = json.loads((PACKET / "ARITHMETIC_001.json").read_text())["values"]
    for key, value in expected.items():
        item = arithmetic[key]
        assert Fraction(int(item["numerator"]), int(item["denominator"])) == value
        assert item["decimal"] == float(value)

    primary = (PACKET / "originals/primary.xml").read_bytes()
    text = (PACKET / "originals/primary_text.txt").read_bytes()
    reference = "source_" + digest(primary)

    def witness(quote):
        raw = quote.encode()
        assert text.count(raw) == 1, quote
        start = text.index(raw)
        return {"source_ref": reference, "representation": "text", "start": start,
                "end": start + len(raw), "quote": quote}

    paragraph = next(line for line in text.decode().splitlines() if "7 mg/ml per Bradford" in line)
    context = witness(paragraph)

    def meaning(value, quote=None):
        return {"value": value, "witnesses": [] if quote is None else [witness(quote)]}

    def quantity(phrase, number, role, method, qualification):
        number_at = phrase.index(number)
        selection = witness(phrase)
        unit_at = selection["start"] + len(phrase[:phrase.index("mg/ml")].encode())
        return {**dict.fromkeys(LITERAL_FIELDS),
                "subject": witness("5 mg/ml HFP") if role == "target_mass_estimate" else None,
                "preparation": context, "stock": context, "method": witness(method),
                "reported_basis": selection, "measurement_identity": selection,
                "measurement": {"number": {"witness": selection, "number_start": number_at,
                                             "number_end": number_at + len(number)},
                                "unit": {"source_ref": reference, "representation": "text",
                                         "start": unit_at, "end": unit_at + 5, "quote": "mg/ml"}},
                "amount_role": {"value": role, "witnesses": [context]},
                "amount_kind": {"value": "estimated" if role == "target_mass_estimate" else "measured",
                                "witnesses": [context]},
                "qualification": meaning(qualification, phrase),
                "basis_status": {"value": "supported", "witnesses": [context]},
                "reported_uncertainty": {"kind": meaning("unreported"), "statement": None}}

    arguments = {"source_ref": reference, "source_kind": "primary_source", "experiment": context,
                 "intended_change": None,
                 "comparison_kind": {"value": "stock_target_mass_estimate_over_total_mass_estimate",
                                     "witnesses": [context]},
                 "pair_relationship": {"value": "supported", "witnesses": [context]},
                 "stock_relationship": {"value": "same", "witnesses": [context]},
                 "quantities": {
                     "numerator": quantity("an approximate concentration of 5 mg/ml HFP", "5",
                                           "target_mass_estimate", "visual inspection of SDS-PAGE gels",
                                           "source_qualified_approximate"),
                     "denominator": quantity("7 mg/ml per Bradford analysis", "7",
                                             "total_protein_mass_estimate", "7 mg/ml per Bradford analysis",
                                             "reported_point")},
                 "covariance_source_ref": None}

    def read_source(source, representation):
        assert source == reference
        data = primary if representation == "original" else text
        return {"artifact_ref": "artifact_" + digest(data), "content": data}

    extraction = read_amount_inputs(arguments, read_source=read_source)
    sheet = populate_amount_components(extraction["calculation_inputs"])
    assert sheet["cells"]["amount_ratio"]["value"] == float(Fraction(5, 7))
    assert sheet["cells"]["conditional_mass_denominator_factor"]["value"] == float(Fraction(7, 5))
    assert sheet["cells"]["amount_ratio"]["approximate"] is True
    assert sheet["cells"]["amount_ratio_variance"]["value"] is None
    assert sheet["cells"]["amount_ratio_variance"]["unavailable_reason"] == "amount_covariance_unreported"
    assert sheet["mass_factor_applied_to_rate"] is False
    for name, value in (("AMOUNT_ARGUMENTS_001.json", arguments),
                        ("AMOUNT_EXTRACTION_001.json", extraction), ("AMOUNT_SHEET_001.json", sheet)):
        write(name, value)
    result = {"status": "passed", "observed_unix": time.time(),
              "frozen_packet_files_verified": len(manifest["files"]),
              "literal_source_spans_verified": spans, "exact_arithmetic_checked": len(expected),
              "DOCX_source_members_verified": 6, "original_DOCX_paragraph_checks": 5,
              "production_calls": ["read_amount_inputs", "populate_amount_components"],
              "new_graders": 0, "new_assay_types": 0,
              "scope": "independent retained-source review and direct existing-reader/calculator execution",
              "not_established": ["selected episode execution for this new example", "quantitative contaminant activity",
                                  "active target fraction", "complete common scientific scoring", "annotation credit"]}
    write("ROOT_CHECK_001.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
