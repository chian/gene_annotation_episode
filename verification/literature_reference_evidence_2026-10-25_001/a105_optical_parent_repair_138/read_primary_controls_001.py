"""Independent retained-primary table arithmetic, not a runtime grader.

No source acquisition, model call, score policy or historical record mutation.
The table supplies reports, not precision or a cross-protocol coupling fraction.
"""
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = self.row = self.cell = None

    def handle_starttag(self, tag, attributes):
        if tag == "table":
            self.table = []
        elif self.table is not None and tag == "tr":
            self.row = []
        elif self.table is not None and tag in ("td", "th"):
            self.cell = []

    def handle_data(self, value):
        if self.cell is not None:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def fraction(value):
    return {"exact": str(value), "value": float(value)}


def main():
    source = Path("research/experimental_scoring_review_2026-10-23/a105_optical_case_031/primary_access_0.bin")
    raw = source.read_bytes()
    expected = "318ac6fe96b509815001892dcaa996688c703175c7dedf88b663d99fe9c90bcf"
    assert hashlib.sha256(raw).hexdigest() == expected
    parser = Tables()
    parser.feed(raw.decode())
    candidates = [table for table in parser.tables
                  if any("Sp act (U/mg)" in cell for row in table for cell in row)]
    assert len(candidates) == 1
    rows = candidates[0]
    blocks, current = {}, None
    for number, row in enumerate(rows):
        if len(row) != 2:
            continue
        label, token = row
        if not token:
            current = label
            blocks[current] = {}
        elif current is not None:
            assert label not in blocks[current]
            blocks[current][label] = {"table_row": number, "label": label, "source_token": token}
    nadh = blocks["NADH oxidation (measured photometrically)"]
    hydrogen = blocks["Ferredoxin reduction (measured via H2 formation in the presence of hydrogenase)"]
    selection = {
        "nadh_reference_25C": nadh["Fd + Hyd"],
        "nadh_methyl_viologen_25C": nadh["Fd + Hyd + methyl viologen"],
        "h2_reference_37C": hydrogen["Fd + Hyd"],
        "h2_methyl_viologen_37C": hydrogen["Fd + Hyd + methyl viologen"],
        "h2_without_crotonyl_37C": hydrogen["Fd + Hyd − crotonyl-CoA"],
    }
    assert selection["nadh_reference_25C"]["source_token"] == "7 (14)a"
    assert selection["nadh_methyl_viologen_25C"]["source_token"] == "5"
    assert selection["h2_reference_37C"]["source_token"] == "5"
    assert selection["h2_methyl_viologen_37C"]["source_token"] == "0.02"
    assert selection["h2_without_crotonyl_37C"]["source_token"] == "<0.01"
    # Table2's footnote defines the parenthesized14 as the37C value.
    # The selected7 is the25C assay, not a second independent observation.
    nadh_ratio = Fraction(selection["nadh_methyl_viologen_25C"]["source_token"])/7
    h2_ratio = Fraction(selection["h2_methyl_viologen_37C"]["source_token"])/5
    limit = Fraction(selection["h2_without_crotonyl_37C"]["source_token"][1:])
    result = {
        "kind": "reported primary table values and derived arithmetic; not a new assay or configured-model run",
        "source_path": str(source), "source_sha256": expected,
        "source_location": "Table2; assay row blocks and footnotes; nominal units endpoint-specific U/mg",
        "selection": selection,
        "nadh_retained_rate_fraction": fraction(nadh_ratio),
        "h2_retained_rate_fraction": fraction(h2_ratio),
        "cross_protocol_retention_difference": fraction(nadh_ratio-h2_ratio),
        "h2_crotonyl_omission_loss_fraction_domain": {
            "lower": fraction(1-limit/5), "lower_inclusive": False,
            "upper": fraction(Fraction(1)), "upper_inclusive": True,
            "conditional_on": "nonnegative true omission rate below reported threshold; reference point report5 used as denominator; no sampling-confidence claim",
        },
        "h2_crotonyl_dependent_rate_domain": {
            "lower": fraction(5-limit), "lower_inclusive": False,
            "upper": fraction(Fraction(5)), "upper_inclusive": True,
            "unit": "umol_H2_per_min_per_mg_complex",
        },
        "cross_protocol_coupling_efficiency": None,
        "statistical_uncertainty": None,
        "independent_preparation_count": None,
        "overall_reliability_score": None,
        "interpretation_limits": [
            "The complex, ferredoxin and hydrogenase coexist; H2 is a coupled downstream endpoint.",
            "Crotonyl omission is the intended mechanistic contrast, not a no-enzyme matched blank.",
            "NADH and H2 assays differ in temperature, reagent concentrations, enzyme loading and reporter conditions.",
            "Within-endpoint fractions describe the specified protocols; their difference is not a calibrated coupling fraction or reliability probability.",
            "The source reports lag phases and rates not always proportional to enzyme amount; mass normalization alone does not establish common-condition catalytic comparability.",
            "No below-limit value was substituted as zero or as the threshold point.",
            "Loss fraction and rate difference share the same observations and cannot be counted as independent evidence.",
        ],
    }
    output = Path(__file__).with_name("PRIMARY_CONTROL_CONVERSION_001.json")
    output.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({key: result[key] for key in (
        "nadh_retained_rate_fraction", "h2_retained_rate_fraction",
        "cross_protocol_retention_difference", "h2_crotonyl_omission_loss_fraction_domain",
        "cross_protocol_coupling_efficiency", "overall_reliability_score")}, indent=2))


if __name__ == "__main__":
    main()
