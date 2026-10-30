"""Retain D1 examples, exact command results and hashes without live access."""
import hashlib
import json
from pathlib import Path
import platform
import re

from gene_annotation_episode import bvbrc_data_fields, bvbrc_data_query


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NATIVE = ROOT / "verification/tool_graders_bvbrc_data_contract_2026-10-24"
BASE = "https://www.bv-brc.org/api"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def query(collection="genome", mode="page", **kwargs):
    return {"version": "bvbrc_data_request_v2", "collection": collection,
            "mode": mode, "filters": [], **kwargs}


def prepare(request, selector=None):
    return bvbrc_data_query.encode_native_query(request, base_url=BASE, page_selector=selector)


assert digest(NATIVE / "D1_QUERY_CONTRACT_FROZEN.json") == "23483aed4a1f84a4ec265a4223f66385322e73a1fc82f9889168f5251586c714"
features = ["PATRIC.511145.12.NC_000913.CDS.822959.823720.rev",
            "RefSeq.511145.12.NC_000913.CDS.822959.823720.rev"]
membership = [{"field": "feature_id", "operator": "in", "value": features}]
facet_request = {"field": "annotation", "offset": 0, "limit": 2, "min_count": 1,
                 "sort": "index", "include_missing": True}
examples = {
    "default_page": prepare(query()),
    "selected_page": prepare(query("genome_feature", fields=["aa_length", "product"],
        sort=[{"field": "aa_length", "direction": "desc"}], offset=5, limit=4), {"offset": 9, "limit": 3}),
    "membership_count": prepare(query("genome_feature", "count", filters=membership)),
    "membership_facet": prepare(query("genome_feature", "facet", filters=membership, facet=facet_request)),
    "strict_open_range": prepare(query(filters=[
        {"field": "genome_id", "operator": "eq", "value": "511145.12"},
        {"field": "genome_length", "operator": "range", "lower": 4639675,
         "lower_inclusive": False, "upper": None, "upper_inclusive": False}])),
    "negative_expression_literal": prepare(query("bioset_result", filters=[
        {"field": "log2_fc", "operator": "eq", "value": -2.5}])),
    "punctuation_literal": prepare(query(filters=[
        {"field": "genome_id", "operator": "eq", "value": 'x") OR *:*&rows=999&fq={!join}%22+\\'}])),
}
save("PREPARED_EXAMPLES.json", examples)

source_paths = [
    ROOT / "gene_annotation_episode/api_bvbrc.py", ROOT / "tests/test_api_bvbrc.py",
    ROOT / "gene_annotation_episode/domain.py", ROOT / "pyproject.toml",
    NATIVE / "D1_QUERY_CONTRACT_FROZEN.json", NATIVE / "field_contract_evidence.json",
    NATIVE / "official/lib__solrjs__rql.js", NATIVE / "official/middleware__RQLQueryParser.js"]
source_paths += [NATIVE / f"schema_{name}.body" for name in bvbrc_data_fields.COLLECTIONS]
for name in ("feature_count_solr", "feature_facet_solr_zero", "solr_range_inclusive",
             "solr_range_exclusive", "range_gt", "range_lt", "range_ge", "range_le"):
    source_paths.extend([NATIVE / (name + ".body"), NATIVE / (name + ".meta.json")])
production_paths = [ROOT / "gene_annotation_episode/bvbrc_data_fields.py",
    ROOT / "gene_annotation_episode/bvbrc_data_query.py", ROOT / "tests/test_bvbrc_data_query.py"]
verification_paths = [HERE / "record_verification.py", HERE / "verify_fresh_process_purity.py",
    HERE / "pytest-initial.json", HERE / "pytest-initial.log", HERE / "pytest-final.json",
    HERE / "pytest-final.log", HERE / "fresh-process-purity.json", HERE / "fresh-process-purity.log",
    HERE / "PREPARED_EXAMPLES.json"]


def records(paths):
    return [{"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
             "sha256": digest(path), "bytes": path.stat().st_size} for path in paths]


save("SOURCE_HASHES.json", {"inputs": records(source_paths),
                            "implementation_and_tests": records(production_paths),
                            "verification": records(verification_paths)})
pytest_record = json.loads((HERE / "pytest-final.json").read_text())
pytest_record["output"] = (HERE / "pytest-final.log").read_text()
purity_record = json.loads((HERE / "fresh-process-purity.json").read_text())
purity_record["output"] = (HERE / "fresh-process-purity.log").read_text()
assert pytest_record["returncode"] == purity_record["returncode"] == 0
assert re.search(r"203 passed in [0-9.]+s", pytest_record["output"])
report = {
    "scope": "D1 pure query preparation only; no BV-BRC service integration claim",
    "frozen_contract_sha256": digest(NATIVE / "D1_QUERY_CONTRACT_FROZEN.json"),
    "python": platform.python_version(),
    "collections": len(bvbrc_data_fields.COLLECTIONS),
    "collection_fields": sum(len(row["fields"]) for row in bvbrc_data_fields.FIELD_REGISTRY.values()),
    "exports": {"bvbrc_data_fields": list(bvbrc_data_fields.__all__),
                "bvbrc_data_query": list(bvbrc_data_query.__all__)},
    "versions": {"field_contract": bvbrc_data_fields.FIELD_CONTRACT_VERSION,
                 "compiler": bvbrc_data_query.COMPILER_VERSION,
                 "request": "bvbrc_data_request_v2", "prepared": "bvbrc_data_prepared_v2",
                 "effective": "bvbrc_data_effective_query_v2", "population": "bvbrc_data_population_v1"},
    "test_execution": pytest_record,
    "fresh_process_purity": purity_record,
    "retained_native_verification": [
        "All 22 schema byte hashes, unique keys and selected field type/cardinality/index/stored flags checked.",
        "Count and facet request URLs/ordered parameters match retained native metadata byte for byte.",
        "Solr range terms agree with retained inclusive equality and strict lower-bound receipts; generated AND parentheses are explicit.",
        "Legacy gt/lt request URLs remain equal to retained native RQL requests and their inclusive equality receipts.",
    ],
    "synthetic_verification": [
        "All registry capability flags, membership and exact int/float/boolean/string types.",
        "Each Solr special character, malicious literal operator text and separate URL encoding.",
        "Mixed/open/equal-exclusive numeric ranges, finite values and malformed/closed syntax.",
        "Omissions, explicit empty sort, custody fields, stable tie breakers and exact page-selector contract.",
        "Population identity stable across windows/fields/sort/mode, distinct across endpoint/collection/filter semantics.",
        "Schemas expand to the exact frozen definitions; populated prepared examples validate against both schemas.",
    ],
    "live_calls_executed": 0, "jobs_submitted": 0,
    "episode_communication_verified": False,
    "remaining_work_outside_D1": [
        "Service execution, retained-response readers, sheets, calculators and complete episode communication binding.",
        "Live D1 compiler execution; special punctuation, mixed ranges and every registered field are not live verified here.",
        "Date ranges and analyzed string_ci equality are unsupported by this fixed contract.",
        "Stable sorting is not an atomic cross-request snapshot; pagination is one explicit page only.",
        "The separate pending NCBI BLAST live-job verification was not accessed.",
    ],
}
save("REPORT.json", report)
print(json.dumps({"scope": report["scope"], "tests": "203 passed", "purity": "passed",
                  "collections": 22, "fields": 318, "live_calls_executed": 0}, sort_keys=True))
