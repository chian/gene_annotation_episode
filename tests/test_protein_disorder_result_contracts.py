"""Pure boundary controls over exact retained231 engineered-wrapper values.

The Source constant exercises lexical schemas only; no Source, custody or live
predictor execution is manufactured. The numerical owner is never rerun here.
"""

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import protein_disorder_result_contracts as contracts


def selection(*rows):
    return dict(version=contracts.SELECTION_VERSION, rows=list(rows))


def request(kind, fields, **identity):
    return dict(row_id=dict(kind=kind, **identity), fields=list(fields))


@pytest.mark.parametrize("bad", [
    request("residue", ["score_value"], row_ordinal=True),
    request("residue", ["score_value"], row_ordinal=1.0),
    request("residue", ["score_value", "score_value"], row_ordinal=0),
    request("residue", ["confidence"], row_ordinal=0),
    request("summary", []),
    request("unknown", ["score_value"]),
])
def test_selection_rejects_ambiguous_identity_or_unregistered_field_without_coercion(bad):
    with pytest.raises(ValueError): contracts.validate_disorder_selection(selection(bad))


def test_every_exported_schema_conforms_to_its_declared_draft_before_validating_instances():
    for kind in ("Selection", "Arguments", "Packet", "Return"):
        Draft202012Validator.check_schema(contracts.protein_disorder_result_schema(kind))
    Draft202012Validator.check_schema(
        contracts.ordinary_disorder_fact_sources()[contracts.FACT_SOURCE]["report_schema"])


