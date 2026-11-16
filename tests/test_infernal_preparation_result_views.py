"""Pure selection over retained native examples; no new native execution.

The occurrence envelopes below are explicitly synthetic test bindings of the
retained descriptors. They preserve actual native digests/bytes/measurements;
root publication and return authentication own real Store/episode bindings.
"""

import pytest

from gene_annotation_episode.episodic_workflow.root.library import infernal_preparation_result_views as views
from gene_annotation_episode.episodic_workflow.root.library import infernal_preparation_models as models
from gene_annotation_episode.episodic_workflow.root.library import infernal_preparation_artifacts as artifacts
from gene_annotation_episode.episodic_workflow.root.library import infernal_preparation_statistics as statistics
from gene_annotation_episode.episodic_workflow.root.library import infernal_preparation_calculations as calculations


def selector(collection="calculations", quantities=(), checks=(), *, rows=None, selected_artifacts=(), projection=True):
    return {"version": "native_infernal_preparation_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": {"collection": collection, "rows": rows or {"offset": 0, "limit": 100000},
                       "quantities": list(quantities), "checks": list(checks)} if projection else None,
        "artifacts": list(selected_artifacts)}


def test_schema_catalogue_has_unsampled_model_fit_fields_and_no_array_expressions():
    catalog = views.preparation_projection_catalog("cmstat", "summary")
    quantities = catalog["input_records"]["quantities"]
    expected = {"fields." + key for key in models.FIELD_UNITS}
    expected |= {"filter_hmm.fields." + key for key in models.HMM_UNITS}
    expected |= {"topology." + key for key in models.TOPOLOGY_FIELDS}
    expected |= {f"calibration.{tag}.{field}" for tag in models.CALIBRATION_ALGORITHMS for field in statistics.VALUE_UNITS["calibration"]}
    expected |= {"efp7gf.location", "efp7gf.scale"}
    assert set(quantities) == expected
    assert quantities["calibration.ECMGI.lambda"]["unit"] == "inverse_bit"
    assert all(entry["meaning"] for entry in quantities.values())
    assert not any(path.startswith(("null_background", "filter_hmm.stats", "series")) for path in quantities)
    catalog["input_records"]["quantities"].clear()
    assert views.preparation_projection_catalog("cmstat", "summary")["input_records"]["quantities"]


@pytest.mark.parametrize("program,mode,selected", [
    ("cmsearch", "search", selector(quantities=["components.residue_count"])),
    ("cmemit", "build", selector(quantities=["components.residue_count"])),
    ("cmemit", "consensus", selector(quantities=["components.output_model_count"])),
    ("cmemit", "consensus", selector("input_records", ["values.gc_count"])),
    ("cmconvert", "binary", selector("output_records", ["fields.CLEN"])),
    ("cmbuild", "build", selector("native_rows", ["values.bit_score_sum"])),
    ("cmstat", "summary", selector("input_records", [], ["model_reference_valid"])),
    ("cmstat", "summary", selector("input_records", ["filter_hmm.stats.0.location"])),
    ("cmstat", "summary", selector("input_records", ["fields.CLEN+fields.W"])),
    ("cmemit", "consensus", selector(quantities=["components.gc_count", "components.gc_count"])),
    ("cmemit", "consensus", selector()),
    ("cmemit", "consensus", selector(projection=False)),
    ("cmemit", "consensus", selector(quantities=["components.gc_count"], rows={"offset": True, "limit": 1})),
    ("cmemit", "consensus", selector(quantities=["components.gc_count"], rows={"offset": 0.0, "limit": 1})),
    ("cmemit", "consensus", selector(quantities=["components.gc_count"], rows={"record_keys": ["same", "same"]})),
])
def test_wrong_program_mode_collection_field_and_expression_rejected(program, mode, selected):
    with pytest.raises(ValueError):
        views.validate_preparation_result_selector(selected, program=program, mode=mode)


def test_selector_copy_and_closed_fields():
    selected = selector(quantities=["components.gc_count"])
    copy = views.validate_preparation_result_selector(selected, program="cmemit", mode="consensus")
    copy["projection"]["quantities"].append("components.residue_count")
    assert selected["projection"]["quantities"] == ["components.gc_count"]
    selected["instructions"] = "arbitrary prose"
    with pytest.raises(ValueError):
        views.validate_preparation_result_selector(selected, program="cmemit", mode="consensus")


