"""Run via python -m from repository root; no I/O after the module imports.

The audit hook intentionally remains active for the lifetime of this process.
This catches first-call lazy I/O that a warmed test process could miss.
"""
import json
import sys

from gene_annotation_episode.bvbrc_data_query import encode_native_query, validate_data_query
from gene_annotation_episode.domain import ContractError


def prohibit_external_io(event, arguments):
    if (event in {"open", "os.listdir", "os.scandir", "os.system", "os.posix_spawn", "os.exec"}
            or event.startswith(("socket.", "subprocess.", "sqlite3."))):
        raise AssertionError("pure D1 operation attempted " + event)


sys.addaudithook(prohibit_external_io)
base = "https://www.bv-brc.org/api"
examples = [
    {"version": "bvbrc_data_request_v2", "collection": "genome", "mode": "page", "filters": []},
    {"version": "bvbrc_data_request_v2", "collection": "genome", "mode": "count",
     "filters": [{"field": "genome_id", "operator": "eq", "value": "511145.12"}]},
    {"version": "bvbrc_data_request_v2", "collection": "genome", "mode": "facet", "filters": [],
     "facet": {"field": "genome_id", "offset": 0, "limit": 2, "min_count": 1,
               "include_missing": True, "sort": "index"}},
]
for example in examples:
    assert validate_data_query(example) == example
    assert encode_native_query(example, base_url=base)["original_request"] == example
page = encode_native_query(examples[0], base_url=base, page_selector={"offset": 5, "limit": 2})
assert page["effective_request"]["offset"] == 5
try:
    validate_data_query({**examples[0], "collection": "unsupported"})
except ContractError as error:
    assert str(error) == "bvbrc_unknown_collection"
else:
    raise AssertionError("invalid collection was accepted")
print(json.dumps({"status": "passed", "first_call_after_import": True,
                  "modes": ["page", "count", "facet"], "explicit_page_selector": True,
                  "invalid_collection": True,
                  "file_network_process_database_audit_hook": "prohibited"}, sort_keys=True))
