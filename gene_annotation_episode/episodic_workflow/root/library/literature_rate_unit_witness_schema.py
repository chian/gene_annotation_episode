from copy import deepcopy
from gene_annotation_episode.domain import REF, obj

def _witness_schema():
    """Full retained witness contract; public input projections omit quote."""
    return obj({"source_ref": REF, "representation": {"enum": ["original", "text"]},
        "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
        "quote": {"type": "string", "minLength": 1}})



_DEFINITION_KEYS = ("bridge", "clause", "amount", "amount_unit", "time_unit",
                    "endpoint", "endpoint_entity", "definition_entity")

def _enriched_schema():
    return obj({**deepcopy(_witness_schema()["properties"]), "artifact_ref": deepcopy(REF)})



def _parsed_number_schema():
    return obj({"selector": obj({"witness": _enriched_schema(),
        "number_start": {"type": "integer", "minimum": 0},
        "number_end": {"type": "integer", "minimum": 1}}),
        "raw_number": {"type": "string", "minLength": 1},
        "value": {"type": "number"}, "relation": {"enum": ["point", "lt", "le"]}})



def parsed_defined_rate_unit_schema():
    fields = {name: _enriched_schema() for name in _DEFINITION_KEYS if name != "amount"}
    fields["amount"] = _parsed_number_schema()
    return obj({"witness": _enriched_schema(), "raw_unit": {"type": "string", "minLength": 1},
        "canonical_unit": {"const": "pmol/min/mg"},
        "multiplier": {"type": "number", "exclusiveMinimum": 0}, "definition": obj(fields)})



