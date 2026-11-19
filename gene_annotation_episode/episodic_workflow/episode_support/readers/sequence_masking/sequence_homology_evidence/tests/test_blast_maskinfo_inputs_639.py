"""Reuse retained 636 native bytes; no native execution or acquisition."""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.sequence_homology_evidence.blast_maskinfo_inputs import parse_blast_maskinfo
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError


def occurrence(content, oid="mask", role="mask", completeness="complete"):
    digest = hashlib.sha256(content).hexdigest()
    return {"occurrence_id": oid, "direction": "output" if role == "mask" else "input", "role": role,
            "ordinal": 0, "artifact_ref": "artifact_" + digest, "sha256": digest,
            "size_bytes": len(content), "completeness": completeness}


def test_synthetic_asn1_single_and_doubled_quote_escape_retains_lexemes():
    data = b'Blast-db-mask-info ::= { algo-id 0, algo-program other, algo-options "a ""quoted"" b", masks { masks { int { from 2, to 3, id local str "x" } }, more FALSE } }\n'
    parsed = parse_blast_maskinfo(data, occurrence=occurrence(data), native_format="maskinfo_asn1_text")
    assert parsed["parse_state"] == "complete", parsed["failures"]
    assert parsed["roots"][0]["algorithm_options"] == 'a "quoted" b'
    assert parsed["records"][0]["native_location_kind"] == "int"
    assert parsed["records"][0]["intervals"][0]["start"] == 2


