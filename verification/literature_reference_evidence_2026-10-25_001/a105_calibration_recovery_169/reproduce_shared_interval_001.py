"""Synthetic reproducer: distinct td values are not one dash-delimited interval.

This file records the unmodified shared reader's behavior. It does not mask an
error or supply replacement scientific values to the new recovery reader.
"""
import hashlib
import json

from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_partner_source_fields import read_source_number

raw = b"<table><tr><td>10</td><td>-2</td></tr></table>"
reference = "source_" + "1"*24
artifact = "artifact_" + hashlib.sha256(raw).hexdigest()
start = raw.index(b"10")
selector = {"witness": {"source_ref": reference, "representation": "original",
    "start": start, "end": start+2, "quote": "10"}, "number_start": 0, "number_end": 2}
sources = _Sources(lambda ref, representation: {"artifact_ref": artifact, "content": raw})
try:
    result = read_source_number(selector, sources=sources, role="rate")
except ExperimentalContractError as error:
    print(json.dumps({"fixture": "synthetic", "status": "rejected", "code": error.code,
                      "field": error.field, "expected": "point 10 from first td"}))
else:
    print(json.dumps({"fixture": "synthetic", "status": "accepted", "value": result["value"],
                      "expected": "point 10 from first td"}))
