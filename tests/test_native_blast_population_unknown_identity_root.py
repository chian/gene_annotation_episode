"""Root review: missing population identity is not a known contradiction.

All reports, assertions and database manifests in these cases are synthetic.
The production metadata preparation and saved-sheet validation paths run;
neither a scientific executable nor external acquisition is invoked.
"""
import json

import pytest

from test_native_blast_database_population_metadata import (
    components, fixture, reseal_synthetic, run, source_change,
)
from gene_annotation_episode.native_blast_standard_database_metadata import (
    validate_standard_blast_database_sheet_set,
)


@pytest.mark.parametrize("field", ["release", "scope"])
@pytest.mark.parametrize("location", ["assertion", "selected_database"])
def test_one_unknown_identity_field_remains_unavailable(field, location):
    inputs, payload = fixture()
    if location == "assertion":
        document = json.loads(inputs["contents"]["artifact-population-assertion"])
        document["assertion"]["population_identity"][field] = None
        source_change(inputs, payload, "population-assertion", document)
    else:
        inputs["job"]["databases"][0]["identity"][field] = None
        reseal_synthetic(inputs)
        document = json.loads(inputs["contents"]["artifact-population-assertion"])
        document["assertion"]["database_manifest_sha256"] = inputs["job"]["databases"][0]["manifest_file"]["sha256"]
        source_change(inputs, payload, "population-assertion", document)
    sheets = run(inputs, payload)
    metadata = sheets["metadata_binding_results"][0]
    issues = metadata["issues"]
    prefix = "blast_database_population_"
    assert not any(i["detail_code"] == prefix + "population_identity_conflict" for i in issues)
    missing = [i for i in issues if i["detail_code"] == prefix + "population_" + field + "_unavailable"]
    assert missing and all(i["code"] == "native_blast_metadata_relation_unresolved" for i in missing)
    result = components(sheets)
    relation = result["database_sheet"]["database_population_relation"]
    assert relation["status"] == "unavailable", relation
    assert result["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert result["function_weights"]["representation_adjusted_probabilities"] is None
    assert validate_standard_blast_database_sheet_set(sheets) == sheets


@pytest.mark.parametrize("field", ["release", "scope"])
def test_known_different_identity_field_remains_a_conflict(field):
    inputs, payload = fixture()
    document = json.loads(inputs["contents"]["artifact-population-assertion"])
    document["assertion"]["population_identity"][field] = "different-known-value"
    source_change(inputs, payload, "population-assertion", document)
    sheets = run(inputs, payload)
    issues = sheets["metadata_binding_results"][0]["issues"]
    assert any(i["detail_code"] == "blast_database_population_population_identity_conflict"
               and i["code"] == "native_blast_metadata_relation_conflict" for i in issues)
    result = components(sheets)
    assert result["database_sheet"]["database_population_relation"]["status"] == "incompatible"
    assert result["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert result["function_weights"]["representation_adjusted_probabilities"] is None
