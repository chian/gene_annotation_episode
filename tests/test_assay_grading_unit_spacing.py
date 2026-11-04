"""Authenticate adjacent units across UTF-8 whitespace in published source text."""
import hashlib

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_assay_grading_inputs import _literal
from gene_annotation_episode.literature_assay_inputs import _Sources


def selection_and_source(gap):
    prefix = "Reported lag difference: ".encode()
    raw = prefix + b"32" + gap + b"min."
    source_ref = "source_" + "a" * 24
    artifact_ref = "artifact_" + hashlib.sha256(raw).hexdigest()
    def witness(token, start):
        return dict(source_ref=source_ref, representation="text", start=start,
            end=start + len(token.encode()), quote=token)
    selection = dict(kind="source_number", origin="reported",
        number=dict(witness=witness("32", len(prefix)), number_start=0, number_end=2),
        unit=witness("min", len(prefix) + 2 + len(gap)))
    sources = _Sources(lambda *_: dict(content=raw, artifact_ref=artifact_ref))
    return selection, sources


@pytest.mark.parametrize("gap", ["", " ", "\t", "\n", "\u2009", "\u00a0", "\u202f", " \u2009 "])
def test_literal_preserves_number_and_unit_across_unicode_whitespace(gap):
    selection, sources = selection_and_source(gap.encode())
    value = _literal(selection, sources)
    assert value["value"] == 32 and value["unit"] == "min" and value["status"] == "point"
    assert value["origin"] == "reported" and len(value["measurement_keys"]) == 1


@pytest.mark.parametrize("gap", [b" hours and 4 ", b"/", b"\xff", "\u200b".encode()])
def test_literal_does_not_treat_content_or_invalid_bytes_as_spacing(gap):
    selection, sources = selection_and_source(gap)
    with pytest.raises(ContractError):
        _literal(selection, sources)
