"""Original supplied source-quantity selection schema; no storage."""
from __future__ import annotations

from gene_annotation_episode.domain import REF, obj

def quantity_population_schema():
    text = {"type": "string", "minLength": 1}
    return obj({"source_ref": REF, "source_kind": {"enum": ["primary_jats", "primary_html", "synthetic_fixture"]},
        **{field: dict(text) for field in ("section_id", "paragraph_id", "subject")},
        "quantity": {"enum": ["specific_activity", "apparent_km"]},
        "analyte": {"type": ["string", "null"], "minLength": 1}})


