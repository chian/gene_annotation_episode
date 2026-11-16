import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location("fixture_support", Path(__file__).resolve().parents[1] / "gene_annotation_episode/episodic_workflow/root/tests/fixtures/bvbrc_fastqutils/bundle/fixture_support.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


@pytest.mark.parametrize("kind,selector", [
    ("population", f.population()),
    ("association", dict(selection="semantic", document_id="hostile", input_pointer="/paired_end_libs/0", recipe_ordinal=4, mate="combined", branch="clean")),
])
def test_available_value_requires_complete_population_or_established_association(kind, selector):
    if kind == "population":
        data = f.build({"reads": (f.fastq(["a"]) + b"@broken\nAC", "fastq")})
    else:
        data, _ = f.seven_family_data()
    result = f.run(data, {"target": f.selection(kind, selector, availability="available_value")})
    assert result["facts"]["target"]["state"] == "missing_value"
    result = f.run(data, {"target": f.selection(kind, selector)})
    assert result["facts"]["target"]["state"] == "satisfied"


def test_all_seven_families_keep_specific_source_links_and_assumptions():
    data, fields = f.seven_family_data()
    result = f.run(data, fields)
    assert result["status"] == "ok"
    records = {name: fact["records"][0] for name, fact in result["facts"].items()}
    assert {r["kind"] for r in records.values()} == {"measurement", "component", "category", "population", "association", "requirements", "request_status"}
    assert records["read_count"]["payload"]["value"] == 2
    assert records["gc"]["payload"]["value"] == 5 / 9
    assert records["errors"]["payload"]["value"] == .001
    assert records["retained"]["payload"]["value"] == .75
    assert records["qc"]["payload"]["value"] == "pass"
    assert records["association"]["payload"]["state"] == "unresolved"
    assert records["status"]["payload"]["satisfied"]
    assert records["errors"]["payload"]["encoding_basis"]["declaration"] == data[2][0]["value"]
    assert "source_declarations" in records["errors"]["source_refs"]


