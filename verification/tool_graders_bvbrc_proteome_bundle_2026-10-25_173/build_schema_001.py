"""Build closed wrapper shapes from exact installed native/host contracts.

This records schema construction, not executable scientific scoring rules.
Imported definitions are namespaced without changing any field semantics.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.bvbrc_appservice_contracts import contract_schema
from gene_annotation_episode.bvbrc_proteome_native_contracts import native_schema
from gene_annotation_episode.bvbrc_proteome_data_contracts import proteome_data_schema
from gene_annotation_episode.bvbrc_proteome_sheet_contracts import proteome_sheet_schema

defs = {}


def obj(**fields):
    return dict(type="object", properties=fields, required=list(fields), additionalProperties=False)


def ref(name):
    return {"$ref": "#/$defs/" + name}


def arr(value):
    return dict(type="array", items=value)


def null(value):
    return {"anyOf": [value, {"type": "null"}]}


def const(value):
    return {"const": value}


def imported(prefix, getter, name):
    schema = getter(name)
    def rename(node):
        if type(node) is dict:
            return {k: ("#/$defs/" + prefix + v[8:] if k == "$ref" else rename(v))
                    for k, v in node.items()}
        if type(node) is list:
            return [rename(v) for v in node]
        return node
    for key, value in schema["$defs"].items():
        renamed = rename(value)
        assert prefix + key not in defs or defs[prefix + key] == renamed
        defs[prefix + key] = renamed
    return ref(prefix + name)


host = lambda n: imported("Host", contract_schema, n)
native = lambda n: imported("Native", native_schema, n)
data = lambda n: imported("Data", proteome_data_schema, n)
sheet = lambda n: imported("Sheet", proteome_sheet_schema, n)
text = dict(type="string", minLength=1)
uint = dict(type="integer", minimum=0)
sha = dict(type="string", pattern="^[0-9a-f]{64}$")
evidence, content = host("SourceEvidence"), host("ContentBinding")
defs["NativeDocumentSelection"] = obj(document_id=text, source_ref=text, raw_artifact_ref=text,
    role=const("proteome_native_projection"), declared_format=host("DeclaredFormat"), source_contract=native("SourceContract"))
defs["ProviderParameters"] = obj(version=const("bvbrc_proteome_bundle_parameters_v1"), analysis_id=text,
    native_documents=arr(ref("NativeDocumentSelection")), primary_document_id=text,
    supplied_data_evidence=null(evidence), calculation_parameters=sheet("NativeCalculationParameters"))
defs["InputSourceSelection"] = {"oneOf": [
    obj(kind=const("original_retained_input"), input_binding_id=text),
    obj(kind=const("acquired_artifact"), source_ref=text, raw_artifact_ref=text),
    obj(kind=const("supplied_snapshot"), content=content, completeness_evidence=null(evidence))]}
defs["InputIndexSelection"] = {"oneOf": [
    obj(mode=const("construct"), parameter_source=data("ParameterSource"), additional_parameter_sources=arr(data("ParameterSource"))),
    obj(mode=const("parsed"), result=data("InputIndexResult"), construction_evidence=evidence)]}
for selection, result, key, fmt in [
    ("InventorySelection", "ProteinInventoryResult", "inventory_key", "protein_fasta_utf8_v1"),
    ("FeatureSnapshotSelection", "FeatureSnapshotResult", "snapshot_key", "bvbrc_genome_feature_json_array_v1"),
    ("GenomeSnapshotSelection", "GenomeSnapshotResult", "snapshot_key", "bvbrc_genome_json_array_v1"),
    ("FeatureSequenceSelection", "FeatureSequenceSnapshotResult", "snapshot_key", "bvbrc_feature_sequence_json_array_v1")]:
    fields = dict(mode=const("raw"), **{key: text}, declared_format=const(fmt), source=ref("InputSourceSelection"))
    if key == "snapshot_key":
        fields["population"] = data("PopulationDescriptor")
    if selection == "FeatureSnapshotSelection":
        fields["coordinate_convention"] = data("CoordinateConvention")
    defs[selection] = {"oneOf": [obj(**fields), obj(mode=const("parsed"), **{key: text}, result=data(result), construction_evidence=evidence)]}
sheet("NativeSheet")
defs["SuppliedData"] = obj(version=const("bvbrc_proteome_supplied_data_v1"),
    original_input_index=null(ref("InputIndexSelection")), inventories=arr(ref("InventorySelection")),
    feature_snapshots=arr(ref("FeatureSnapshotSelection")), genome_snapshots=arr(ref("GenomeSnapshotSelection")),
    sequence_snapshots=arr(ref("FeatureSequenceSelection")), execution_links=arr(ref("SheetExecutionInputLink")),
    native_links=arr(ref("SheetNativeProteinLink")), metadata_links=arr(ref("SheetProteinMetadataLink")),
    representation_links=arr(ref("SheetRepresentationLink")))
defs["SuppliedValue"] = obj(evidence=evidence, value=host("Json"))
defs["ResolutionOutcome"] = obj(
    selector_kind={"enum": ["native_document", "original_input_index", "inventory", "feature_snapshot", "genome_snapshot", "sequence_snapshot"]},
    selection_index=uint, state={"enum": ["resolved", "partial", "missing", "invalid", "incompatible", "unverified"]},
    content=null(content), construction_evidence=null(evidence), result_index=null(uint), requirement_ids=arr(text))
defs["ProviderSheet"] = obj(version=const("bvbrc_proteome_provider_sheet_v1"), analysis_id=text,
    original_task=host("OriginalTask"), parameters=ref("ProviderParameters"), requested_form=host("Json"), bundle_sha256=sha,
    supplied_values=arr(ref("SuppliedValue")), input_resolution=arr(ref("ResolutionOutcome")),
    native_results=arr(native("NativeProjectionResult")), input_index_result=null(data("InputIndexResult")),
    inventory_results=arr(data("ProteinInventoryResult")), feature_results=arr(data("FeatureSnapshotResult")),
    genome_results=arr(data("GenomeSnapshotResult")), sequence_results=arr(data("FeatureSequenceSnapshotResult")),
    joins_result=null(sheet("NativeJoinsResult")), native_sheet_result=null(sheet("NativeSheetResult")),
    requirements=arr(host("AcquisitionRequirement")), diagnostics=arr(host("Diagnostic")))
document = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": defs}
path = ROOT / "gene_annotation_episode/bvbrc_proteome_bundle_schemas.json"
path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
print(str(path))
