"""Original engineered table fixture consumed by actual A106 adapters."""
from copy import deepcopy
import hashlib
from gene_annotation_episode.episodic_workflow.root.a106 import bvbrc_intervention_contracts as contracts
from gene_annotation_episode.episodic_workflow.root.a106 import bvbrc_tnseq_bundle_adapter as tnseq
from gene_annotation_episode.episodic_workflow.root.a106 import bvbrc_rnaseq_bundle_adapter as rnaseq
from gene_annotation_episode.episodic_workflow.root.a106.library import bvbrc_application_facts as returns
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical
from .annotation_bundle_fixtures import arguments as annotation_arguments

TRANSIT = (b"#Resampling\n#Normalization: TTR; pseudocount=1\n"
    b"#Orf\tName\tDesc\tSites\tMean Ctrl\tMean Exp\tlog2FC\tSum Ctrl\tSum Exp\tDelta Mean\tp-value\tAdj. p-value\n"
    b"geneA\talpha\tSynthetic fixture\t12\t80\t20\t-1.95\t960\t240\t-60\t0.001\t0.02\n")

DESEQ = (b"Gene_Name\tbaseMean\tlog2FoldChange\tlfcSE\tstat\tpvalue\tpadj\n"
    b"geneA\t20\t-2\t0.5\t-4\t0.0001\t0.001\n"
    b"geneB\t0\tNA\tNA\tNA\tNA\tNA\n")

def arguments(application="TnSeq", raw=None, representation=None):
    raw = (TRANSIT if application == "TnSeq" else DESEQ) if raw is None else raw
    representation = representation or ("transit_resampling" if application == "TnSeq" else "deseq2")
    args = annotation_arguments(raw=raw)
    task = args["bundle"]["original_task"]
    task.update(required_application_id=application, native_application_id=application,
        submitted_parameters={"reference_genome_id": "fixture.reference", "contrasts": [[0, 1]],
            "recipe": "resampling" if application == "TnSeq" else "HTSeq-DESeq"})
    args["bundle"]["artifacts"][0]["declared_format"]["format"] = "tsv"
    args["parameters"].update(version=contracts.PARAMETERS_VERSION, application_id=application)
    args["parameters"]["documents"][0]["representation"] = representation
    args["requested_form"] = contracts.requested_form_schema([dict(field="measurements", selection=dict(
        version=contracts.SELECTION_VERSION, document_id="genome", kind="records", ordinals=None,
        offset=0, limit=100, member_names=None))])
    return args

def consume(args):
    return (tnseq if args["parameters"]["application_id"] == "TnSeq" else rnaseq).consume_bundle(**args)

def publication(args, result):
    def content(value, char):
        raw = canonical(value).encode()
        digest = hashlib.sha256(raw).hexdigest()
        return dict(source_ref="source_" + char * 24, artifact_field="artifact_ref", artifact_ref="artifact_" + digest,
            sha256=digest, byte_count=len(raw))
    selector = dict(version="bvbrc_appservice_result_selector_v1", endpoint="requested_projection",
        requirements=[dict(requirement_id="native-genome", role="caller_selected_gto", required=True,
            declared_format=deepcopy(args["bundle"]["artifacts"][0]["declared_format"]),
            producer_rule_evidence=None, exact_object=None)],
        adapter=dict(adapter_id=result["adapter_id"], adapter_version="1", parameters=args["parameters"]),
        requested_schema=args["requested_form"], supplied_metadata=[], supplied_contents=[], supplied_capabilities=[])
    saved = {key: deepcopy(result[key]) for key in ("adapter_id", "adapter_version", "status", "facts", "missing_requirements", "diagnostics")}
    saved.update(sheet_content=content(result["sheet"], "a"), components_content=content(result["components"], "b"))
    ref = "source_" + "f" * 24
    return dict(version=returns.RESULT_VERSION, source_ref=ref, reference=ref,
        publication=dict(bundle_content=content(args["bundle"], "f"), result_record_refs=[ref], adapter_result=saved),
        publication_inputs=dict(selector=selector, adapter=selector["adapter"], adapter_implementation_sha256=tnseq.implementation_sha256()),
        assignment=dict(selector=selector), record_refs=[ref], bundle=args["bundle"])
