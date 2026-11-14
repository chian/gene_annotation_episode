"""Original structure operation declarations and closed argument schema."""
from copy import deepcopy
from gene_annotation_episode.domain import REF, obj
from ..literature_assay_inputs import SOURCE_KINDS, _nullable
from .literature_rate_unit_witness_schema import _witness_schema

VERSION = "a111_structure_inputs_v1"
SCOPE = "conditional_deposited_model_geometry"
LITERAL_FIELDS = ("molecule", "construct", "experimental_system", "condition", "partner", "experiment")
_ARGS = ("source_ref", "coordinate_source_ref", "validation_source_ref", "source_kind",
         "model_number", "literals", "geometry_panel", "local_panel", "evaluation_scope")
_RESIDUE = ("auth_chain", "auth_seq_id", "insertion_code", "comp_id", "alt_id")
_ENDPOINT = (*_RESIDUE, "atom_names")
_GEOMETRY = ("endpoint_a", "endpoint_b", "positive_max_A", "incompatible_min_A")
_REQUIRED_ATOM = ("group_PDB", "id", "auth_atom_id", "auth_comp_id", "auth_asym_id", "auth_seq_id",
                  "label_alt_id", "pdbx_PDB_ins_code", "Cartn_x", "Cartn_y", "Cartn_z",
                  "occupancy", "B_iso_or_equiv", "pdbx_PDB_model_num")
_SCHEMA_ATTR = "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation"


def structure_population_schema():
    """Closed operation arguments; proposed cutoffs are the only numeric points."""
    text = {"type": "string", "format": "structure_identifier"}
    residue = {field: deepcopy(text) for field in _RESIDUE}
    residue["auth_seq_id"] = {"type": "string", "format": "structure_residue_number"}
    residue["insertion_code"] = {"type": "string", "format": "structure_insertion_code"}
    endpoint = obj({**deepcopy(residue), "atom_names": {"type": "array", "minItems": 1,
        "uniqueItems": True, "items": deepcopy(text)}})
    schema = obj({"source_ref": deepcopy(REF), "coordinate_source_ref": deepcopy(REF),
        "validation_source_ref": _nullable(deepcopy(REF)), "source_kind": {"enum": list(SOURCE_KINDS)},
        "model_number": {"type": "integer", "minimum": 1},
        "literals": obj({field: _nullable(_witness_schema()) for field in LITERAL_FIELDS}),
        "geometry_panel": {"type": "array", "items": obj({"endpoint_a": deepcopy(endpoint),
            "endpoint_b": deepcopy(endpoint), "positive_max_A": {"type": "number", "minimum": 0},
            "incompatible_min_A": {"type": "number", "exclusiveMinimum": 0}})},
        "local_panel": {"type": "array", "items": obj(residue)},
        "evaluation_scope": {"enum": [SCOPE]}})
    from .literature_experiment_assessments import assessment_schema
    from .literature_structure_types import EXPERIMENT_TYPES
    schema["properties"]["experiment_assessment"] = assessment_schema(EXPERIMENT_TYPES)
    return schema


