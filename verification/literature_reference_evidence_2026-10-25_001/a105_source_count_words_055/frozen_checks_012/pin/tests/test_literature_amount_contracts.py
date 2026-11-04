"""Closed source-selector contracts and unwired recurring amount instructions."""
import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_amount_inputs import amount_arguments_schema
from gene_annotation_episode.literature_amount_prompt import AMOUNT_TASK


def unknown():
    return {"value": "unknown", "witnesses": []}


def arguments():
    return {"source_ref": "source_" + "1" * 24, "source_kind": "primary_source", "experiment": None,
        "comparison_kind": unknown(), "pair_relationship": unknown(), "stock_relationship": unknown(),
        "intended_change": None, "quantities": {"numerator": None, "denominator": None},
        "covariance_source_ref": None}


def test_schema_accepts_explicit_unknown_without_public_gene_name():
    validate_schema(arguments(), amount_arguments_schema())


def test_every_closed_object_property_is_required_including_nullable_fields():
    def check(node):
        if isinstance(node, dict):
            if "properties" in node:
                assert set(node["required"]) == set(node["properties"])
                assert node["additionalProperties"] is False
            for child in node.values():
                check(child)
        elif isinstance(node, list):
            for child in node:
                check(child)
    check(amount_arguments_schema())


@pytest.mark.parametrize("field", list(arguments()))
def test_omitting_explicit_null_or_unknown_is_invalid(field):
    args = arguments()
    args.pop(field)
    with pytest.raises(ContractError, match="representation_error"):
        validate_schema(args, amount_arguments_schema())


def test_schema_calls_for_selectors_instead_of_model_authored_scientific_numbers():
    schema = amount_arguments_schema()
    def number_fields(node, path=()):
        if isinstance(node, dict):
            if node.get("type") in ("number", "integer"):
                yield path[-1]
            for key, child in node.items():
                yield from number_fields(child, (*path, key))
        elif isinstance(node, list):
            for child in node:
                yield from number_fields(child, path)
    assert set(number_fields(schema)) <= {"start", "end", "number_start", "number_end"}


def test_prompt_is_aspect_specific_and_preserves_scientific_qualifications():
    for text in ("different measurands", "mass-fraction estimate", "never automatically validated purity",
        "ratio above one", "nominal recipe amount", "public searchable name is not required",
        "reported-point selection cannot override", "missing covariance stays unknown",
        "already target-normalized", "effect isolation"):
        assert text.lower() in AMOUNT_TASK.lower()
    assert "amount_ratio_variance" not in AMOUNT_TASK
    assert "J_transpose" not in AMOUNT_TASK
    assert "scoring_rubric" not in AMOUNT_TASK
