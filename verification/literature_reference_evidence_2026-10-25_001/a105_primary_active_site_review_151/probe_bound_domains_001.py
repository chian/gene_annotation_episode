"""Independent synthetic probe of physical fraction versus measured density."""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
PIN = HERE / "pin_001"
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / "tests")]
from test_a105_active_site_numerical_audit_153 import synthetic_case
from gene_annotation_episode.literature_active_site_inputs import read_active_site_inputs
from gene_annotation_episode.literature_active_site_calculations import populate_active_site_components


def calculate(token):
    arguments, reader, _ = synthetic_case(active=token)
    number = arguments["quantities"]["active_site_concentration"]["measurement"]["number"]
    number["number_start"] = len(token) - len(token.lstrip("<>="))
    extraction = read_active_site_inputs(arguments, read_source=reader)
    result = populate_active_site_components(extraction)
    return {name: result["cells"][name] for name in (
        "sites_per_total_monomer", "conditional_active_monomer_fraction",
        "conditional_nominal_to_active_denominator_factor")}


def main():
    target = HERE / "ROOT_BOUND_DOMAINS_001.json"
    if target.exists():
        raise RuntimeError("Do not overwrite a retained numerical probe")
    cases = {token: calculate(token) for token in (">10", ">=10", "<16")}
    greater = cases[">10"]
    assert greater["sites_per_total_monomer"]["exact_domain"]["lower"] == {"numerator": "1", "denominator": "1"}
    assert greater["sites_per_total_monomer"]["exact_domain"]["lower_inclusive"] is False
    assert greater["conditional_active_monomer_fraction"]["unavailable_reason"] == "active_fraction_exceeds_one"
    assert cases[">=10"]["conditional_active_monomer_fraction"]["value"] == 1
    less = cases["<16"]
    assert less["sites_per_total_monomer"]["exact_domain"]["upper"] == {"numerator": "8", "denominator": "5"}
    assert less["sites_per_total_monomer"]["exact_domain"]["upper_inclusive"] is False
    assert less["conditional_active_monomer_fraction"]["exact_domain"]["upper"] == {"numerator": "1", "denominator": "1"}
    assert less["conditional_active_monomer_fraction"]["exact_domain"]["upper_inclusive"] is True
    assert "physical_one_site_fraction_in_unit_interval" in less["conditional_active_monomer_fraction"]["conditional_on"]
    result = {"scope": "Three synthetic logical-bound counterexamples, not paper observations or scientific adequacy",
        "passed": True, "cases": cases}
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "cases": list(cases)}))


if __name__ == "__main__":
    main()
