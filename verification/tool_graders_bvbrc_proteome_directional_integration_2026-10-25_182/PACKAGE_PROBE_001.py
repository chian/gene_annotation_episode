"""Exercise the installed v2 provider with supplied controlled native inputs.

This verifies package data and pure numerical projection, not service execution
or publication custody. The controlling harness passes an extracted wheel path.
"""
import hashlib
import importlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

installed = Path(sys.argv[1]).resolve()
specimen_path = Path(sys.argv[2]).resolve()
sys.path.insert(0,str(installed))
from gene_annotation_episode import bvbrc_proteome_bundle_adapter_v2 as provider
from gene_annotation_episode.bvbrc_proteome_bundle_adapter import implementation_sha256 as legacy_pin

assert Path(provider.__file__).resolve().is_relative_to(installed)
assert provider.ADAPTER_ID == "bvbrc_proteome" and provider.ADAPTER_VERSION == "2"
specimen = json.loads(specimen_path.read_text())
assert set(specimen) == {"bundle","artifact_files","supplied_values","parameters"}
raw = {}
for reference, name in specimen["artifact_files"].items():
    path = (specimen_path.parent/name).resolve()
    assert path.is_relative_to(specimen_path.parent)
    raw[reference] = path.read_bytes()
native_hash = "e8bcff01bf827d936c36f00e4bbb73f2b5b1dd99b4d37af4cb9a6b0de44e25f8"
assert any(hashlib.sha256(value).hexdigest() == native_hash for value in raw.values())
parameters = provider.validate_parameters(specimen["parameters"])
assert not parameters["native_documents"] and len(parameters["directional_documents"]) == 1
document = parameters["directional_documents"][0]["document_id"]
selectors = {
    "coverage": {"kind":"directional_coverage","scope":"query",
                 "document_id":document,"query_ordinal":1,
                 "metric":"any_displayed_subject_query_paired_union"},
    "symbol_identity": {"kind":"directional_fraction","scope":"subject",
                        "document_id":document,"query_ordinal":1,"subject_ordinal":0,
                        "metric":"compatible_unique_pair_symbol_identity"},
    "resolved_identity": {"kind":"directional_fraction","scope":"subject",
                          "document_id":document,"query_ordinal":1,"subject_ordinal":0,
                          "metric":"compatible_unique_pair_resolved_identity"},
    "expectation": {"kind":"directional_native_decimal","scope":"hsp",
                    "document_id":document,"query_ordinal":1,"subject_ordinal":0,
                    "hsp_ordinal":1,"metric":"expect"},
}
form = provider.requested_form_schema(selectors)
assert provider.validate_requested_form(form) == form

def forbidden(*args,**kwargs):
    raise AssertionError("pure installed provider attempted network or process execution")

with patch("socket.socket",side_effect=forbidden), patch("socket.create_connection",side_effect=forbidden), patch("subprocess.Popen",side_effect=forbidden):
    result = provider.consume_bundle(specimen["bundle"],artifact_bytes=raw,
                                    supplied_values=specimen["supplied_values"],
                                    requested_form=form,parameters=parameters)
assert result["adapter_id"] == "bvbrc_proteome" and result["adapter_version"] == "2"
assert result["status"] == "ok", result
facts = result["facts"]
assert set(facts) == set(selectors)
assert all(value["availability"] == "available" for value in facts.values())
coverage = facts["coverage"]["coverage"]["value"]
symbol = facts["symbol_identity"]["cell"]["value"]
resolved = facts["resolved_identity"]["cell"]["value"]
assert (coverage["numerator"],coverage["denominator"]) == (529,600)
assert (symbol["numerator"],symbol["denominator"]) == (468,529)
assert (resolved["numerator"],resolved["denominator"]) == (468,468)
assert facts["resolved_identity"]["pair_population"] == {
    "total_pairs":529,"resolved_pairs":468,"unresolved_pairs":61,"stop_containing_pairs":0}
assert facts["expectation"]["cell"] == {"state":"present","value":{"sign":0,"digits":[2],"exponent":-66}}
assert facts["expectation"]["expectation_display"] == "positive_reported_decimal"
assert all(value["context"]["operand_binding"] == "unbound" for value in facts.values())
modules = {}
for name,module in sorted(sys.modules.items()):
    if name == "gene_annotation_episode" or name.startswith("gene_annotation_episode."):
        location = getattr(module,"__file__",None)
        if location is not None:
            location = Path(location).resolve()
            assert location.is_relative_to(installed), (name,str(location))
            modules[name] = str(location.relative_to(installed))
print(json.dumps({"adapter_id":result["adapter_id"],"adapter_version":result["adapter_version"],
                  "status":result["status"],"coverage":coverage,"symbol_identity":symbol,
                  "resolved_identity":resolved,"pair_population":facts["resolved_identity"]["pair_population"],
                  "native_expectation":facts["expectation"]["cell"]["value"],
                  "directional_operand_binding":"unbound","implementation_sha256":provider.implementation_sha256(),
                  "legacy_implementation_sha256":legacy_pin(),"imported_modules":modules,
                  "live_service_execution_verified":False,"authenticated_publication_verified":False}))
