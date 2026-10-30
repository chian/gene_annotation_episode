"""Populate original graph measurements without changing scientific run state.

Source/axis/colour interpretation is declared in the retained recipe. This is
direct reader execution, not selected LiteratureEpisodes or typed delivery.
"""
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.literature_figure_measurements import (
    compare_ordinate_cells, read_bar_ordinate,
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    directory = BASE / "primary_f420_partner_013"
    recipe = json.loads((directory / "NATIVE_BAR_SELECTIONS_001.json").read_bytes())
    output = directory / "NATIVE_ORDINATES_001.json"
    if output.exists():
        raise FileExistsError(output)
    tops = {"figure2C_MycB3_Mjan_3PG": 324, "figure6B_standard_3PG": 554,
            "figure6B_standard_2PL": 853, "figure6B_standard_PEP": 1001,
            "figure6B_cognate_3PG": 360, "figure6B_cognate_2PL": 1038,
            "figure6B_cognate_PEP": 1064}
    rows = {}
    for row in recipe["rows"]:
        image_path = directory / row["image"]
        assert sha(image_path) == recipe["image_sha256"][row["image"]]
        result = read_bar_ordinate(image_path.read_bytes(), row["selection"])
        assert result["cell"]["status"] == "populated", (row["quantity"], result)
        assert result["pixel_edge"]["top_row"] == tops[row["quantity"]]
        # Independent exact linear calibration check, no imported arithmetic helper.
        calibration = row["selection"]["calibration"]
        p, v = (Fraction(calibration["first"][key]) for key in ("pixel", "value"))
        q, w = (Fraction(calibration["second"][key]) for key in ("pixel", "value"))
        y = Fraction(tops[row["quantity"]])
        tolerance = Fraction(row["selection"]["edge_tolerance_pixels"])
        f = lambda pixel: v + (pixel - p) * (w - v) / (q - p)
        expected = f(y + Fraction(1, 2))
        lo, hi = sorted((f(y - tolerance), f(y + 1 + tolerance)))
        assert result["cell"]["value"] == float(expected)
        assert Fraction(result["cell"]["lower"]) <= lo <= hi <= Fraction(result["cell"]["upper"])
        rows[row["quantity"]] = {"pair": row["pair"], "product": row["product"],
                                  "panel": row["panel"], "measurement": result}
    comparisons = {}
    pairs = {"figure2C_minus_figure6B_nominal_standard_pair":
             ("figure2C_MycB3_Mjan_3PG", "figure6B_standard_3PG"),
             **{"cognate_minus_standard_" + product:
                ("figure6B_cognate_" + product, "figure6B_standard_" + product)
                for product in ("3PG", "2PL", "PEP")}}
    for name, (first, second) in pairs.items():
        result = compare_ordinate_cells(rows[first]["measurement"]["cell"],
                                       rows[second]["measurement"]["cell"])
        assert result["cell"]["unit"] == "relative_turnover_percentage_points"
        comparisons[name] = {"first": first, "second": second, "result": result}
    files = [ROOT / "gene_annotation_episode/literature_figure_measurements.py",
             ROOT / "gene_annotation_episode/domain.py", Path(__file__),
             ROOT / "tests/test_literature_figure_measurements.py"]
    receipt = {"status": "passed", "written_utc": datetime.now(timezone.utc).isoformat(),
               "version": "f420_native_ordinate_execution_001", "source": recipe["source_doi"],
               "recipe_sha256": sha(directory / "NATIVE_BAR_SELECTIONS_001.json"),
               "executed_source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in files},
               "measurements": rows, "comparisons": comparisons,
               "source_text_3PG_percent": 65,
               "native_percentages_renormalized": False,
               "reported_SD_extracted": False, "independent_preparation_count": None,
               "molar_response_calibration": None, "partner_omission_effect": None,
               "single_CofC_specificity": None, "target_correspondence": "not_evaluated",
               "overall_experimental_reliability": None, "annotation_credit": None,
               "selected_episode_and_typed_return_verified": False,
               "actual_model_interpretation": False,
               "limits": recipe["digitization_assumptions"] + [
                   "Different plotted means do not establish statistical inconsistency or a publication error",
                   "Reported SD and covariance are not supplied by edge digitization",
                   "Partner-swap ordinate differences do not establish omission necessity",
                   "The reader remains unbound to selected LiteratureEpisodes in this increment"]}
    output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "passed", "bars": len(rows),
        "values": {key: value["measurement"]["cell"]["value"] for key, value in rows.items()},
        "differences": {key: value["result"]["cell"] for key, value in comparisons.items()}}, indent=2))


if __name__ == "__main__":
    run()
