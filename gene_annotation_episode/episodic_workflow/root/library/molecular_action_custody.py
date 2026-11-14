"""Selected molecular action and original producer custody.

These checks join the original invocation, request, receipt and runtime rows.
They preserve pending recovery identity and grant no new source or file access.
"""
from copy import deepcopy
import hashlib
import json

from gene_annotation_episode.domain import ContractError, canonical


ITC_TOOL = "analyze_itc_binding_thermodynamics"
RESULT_VERSION = "ordinary_itc_result_v1"


def authenticate_itc_invocation(registry, name, arguments, scope, operation_key):
    """A host context is necessary but its actual saved action is authoritative."""
    invocation = registry._current_invocation.get()
    if invocation is None:
        raise ContractError("molecular_tool_current_invocation_required")
    context, reader, selected_name, selected_arguments, selected_key = invocation
    from gene_annotation_episode.episodic_workflow.root.communication import plain
    from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="molecular_tool_")
    records.authenticate(context)
    prefix = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(prefix):] if isinstance(operation_key, str) and operation_key.startswith(prefix) else ""
    if (not suffix.isdecimal() or str(int(suffix)) != suffix or selected_name != name
            or canonical(selected_arguments) != canonical(arguments) or selected_key != operation_key
            or canonical(plain(context.scope)) != canonical(scope) or not callable(reader)):
        raise ContractError("molecular_tool_selected_action_conflict")
    row = registry.store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
        "AND decision_index=?", (context.run_id, context.episode_id, int(suffix))).fetchone()
    if row is None or canonical(json.loads(row["action"])) != canonical(
            dict(kind="tool", tool=name, arguments=arguments)):
        raise ContractError("molecular_tool_selected_action_conflict")
    return context, reader


authenticate_molecular_invocation = authenticate_itc_invocation


def _publication_profile(tool_name):
    """Finite ordinary producers; a saved read never becomes a new producer."""
    if tool_name == "generate_gene_embeddings_with_ESM_models":
        return ("esm_gene_embedding_result_v1", "ordinary_esm_gene_embedding_publication_v1",
            ("embed",), "esm_gene_embedding_")
    if tool_name == "detect_and_annotate_somatic_mutations":
        return ("ordinary_somatic_variant_result_v1", "ordinary_somatic_variant_publication_v1",
            ("run_native", "calculate_saved"), "somatic_variant_")
    if tool_name == "analyze_protein_phylogeny":
        return ("ordinary_protein_phylogeny_result_v1", "ordinary_protein_phylogeny_publication_v1",
            ("run_native", "calculate_saved"), "protein_phylogeny_")
    if tool_name == "analyze_protein_conservation":
        return ("ordinary_protein_conservation_result_v1", "ordinary_protein_conservation_publication_v1",
            ("run_native", "calculate_saved"), "protein_conservation_")
    if tool_name == "predict_protein_disorder_regions":
        return ("ordinary_protein_disorder_result_v1", "ordinary_protein_disorder_publication_v1",
            ("predict", "calculate_saved"), "protein_disorder_")
    if tool_name == "analyze_arsenic_speciation_hplc_icpms":
        return ("ordinary_arsenic_speciation_result_v1", "ordinary_arsenic_speciation_publication_v1",
            ("calculate", "calculate_saved"), "arsenic_speciation_")
    if tool_name == "result.variants.vcf":
        return ("ordinary_vcf_result_v1", "ordinary_vcf_publication_v1",
            ("analyze", "calculate_saved"), "vcf_result_")
    if tool_name == ITC_TOOL:
        return RESULT_VERSION, "ordinary_itc_publication_v1", ("fit", "calculate_saved"), "ordinary_itc_"
    if tool_name == "liftover_coordinates":
        return "ordinary_liftover_result_v1", "ordinary_liftover_publication_v1", ("convert",), "ordinary_liftover_"
    if tool_name == "analyze_circular_dichroism_spectra":
        return "ordinary_cd_result_v1", "ordinary_cd_publication_v1", ("calculate",), "circular_dichroism_"
    if tool_name == "analyze_cas9_mutation_outcomes":
        return ("ordinary_reference_edit_outcome_result_v1", "ordinary_reference_edit_outcome_publication_v1",
            ("analyze", "calculate_saved"), "reference_edit_outcome_")
    if tool_name == "result.macs2.peaks":
        return ("ordinary_macs2_peak_result_v1", "ordinary_macs2_peak_publication_v1",
            ("parse", "project_saved"), "macs2_peak_")
    if tool_name == "find_enriched_motifs_with_homer":
        return ("ordinary_homer_motif_result_v1", "ordinary_homer_motif_publication_v1",
            ("run_native", "calculate_saved"), "homer_motif_")
    if tool_name == "identify_transcription_factor_binding_sites":
        return ("ordinary_tf_binding_result_v1", "ordinary_tf_binding_publication_v1",
            ("run_native", "calculate_saved"), "tf_binding_")
    if tool_name == "analyze_protease_kinetics":
        return ("ordinary_protease_kinetics_result_v1", "ordinary_protease_kinetics_publication_v1",
            ("run_native", "calculate_saved"), "protease_kinetics_")
    raise ContractError("molecular_publication_unknown_producer")


def _recorded_molecular_action_details(registry, context, arguments, operation_key, tool_name, *,
        recovery_context=None, recovery_operation_key=None, selected_only=False):
    """Authenticate one editing action independently of its Source producer."""
    from gene_annotation_episode.episodic_workflow.root.communication import plain
    from gene_annotation_episode.domain import identity
    from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
    from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.episodic_workflow.root.wait_events import validate_pending
    prefix = ("somatic_variant_" if tool_name == "detect_and_annotate_somatic_mutations" else "esm_gene_embedding_" if tool_name == "generate_gene_embeddings_with_ESM_models" else
        "protein_phylogeny_" if tool_name == "analyze_protein_phylogeny" else
        "protein_conservation_" if tool_name == "analyze_protein_conservation" else
        "protein_disorder_" if tool_name == "predict_protein_disorder_regions" else
        "arsenic_speciation_" if tool_name == "analyze_arsenic_speciation_hplc_icpms" else
        "vcf_result_" if tool_name == "result.variants.vcf" else
        "macs2_peak_" if tool_name == "result.macs2.peaks" else
        "homer_motif_" if tool_name == "find_enriched_motifs_with_homer" else
        "tf_binding_" if tool_name == "identify_transcription_factor_binding_sites" else
        "protease_kinetics_" if tool_name == "analyze_protease_kinetics" else "reference_edit_outcome_")
    if tool_name not in {"analyze_cas9_mutation_outcomes", "result.macs2.peaks", "find_enriched_motifs_with_homer",
            "identify_transcription_factor_binding_sites", "result.variants.vcf",
            "analyze_protease_kinetics", "analyze_arsenic_speciation_hplc_icpms",
            "predict_protein_disorder_regions", "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations",
            "generate_gene_embeddings_with_ESM_models"} or not isinstance(context, BindingContext):
        raise ContractError(prefix + "action_conflict")
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix=prefix)
    records.authenticate(context)
    start = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(start):] if type(operation_key) is str and operation_key.startswith(start) else ""
    if not suffix.isdecimal() or str(int(suffix)) != suffix:
        raise ContractError(prefix + "action_conflict")
    if type(selected_only) is not bool or selected_only and tool_name not in {
            "find_enriched_motifs_with_homer", "identify_transcription_factor_binding_sites",
            "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations"}:
        raise ContractError(prefix + "action_conflict")
    if selected_only:
        # Metadata-only denial authority for a private native capture produced
        # before its public ToolOperation commits. This grants no read/recovery.
        selected = registry.store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? AND decision_index=?", (context.run_id, context.episode_id, int(suffix))).fetchone()
        if selected is None:
            raise ContractError(prefix + "action_conflict")
        actual_selection = json.loads(selected["action"])
        if arguments is None:
            if (type(actual_selection) is not dict or set(actual_selection) != {"kind", "tool", "arguments"}
                    or actual_selection["kind"] != "tool" or actual_selection["tool"] != tool_name):
                raise ContractError(prefix + "action_conflict")
            arguments = actual_selection["arguments"]
        if canonical(actual_selection) != canonical(
                dict(kind="tool", tool=tool_name, arguments=arguments)):
            raise ContractError(prefix + "action_conflict")
        from gene_annotation_episode.execution_contracts import digest as execution_digest
        invocation = dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
            decision_index=int(suffix), request_sha256=execution_digest(plain(context.request)), scope=plain(context.scope))
        return dict(arguments=deepcopy(arguments), invocation=invocation, outcome=None,
            operation_ref=identity("operation", dict(key=operation_key, name=tool_name, arguments=arguments)),
            runtime_outcome=None if selected["result"] is None else json.loads(selected["result"]), pending_recovery=False)
    row = registry.store.db.execute("""SELECT operation.*, action.action AS selected_action,
        action.result AS runtime_outcome FROM tool_operations operation JOIN runtime_actions action
          ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index
        WHERE operation.operation_key=? AND action.run_id=? AND action.episode_id=? AND action.decision_index=?""",
        (operation_key, context.run_id, context.episode_id, int(suffix))).fetchone()
    expected = identity("operation", dict(key=operation_key, name=tool_name, arguments=arguments))
    if (row is None or row["id"] != expected or row["name"] != tool_name
            or row["arguments"] != canonical(arguments) or row["scope"] != canonical(plain(context.scope))
            or canonical(json.loads(row["selected_action"])) != canonical(dict(kind="tool", tool=tool_name, arguments=arguments))):
        raise ContractError(prefix + "action_conflict")
    outcome = json.loads(row["result"])
    runtime = None if row["runtime_outcome"] is None else json.loads(row["runtime_outcome"])
    if type(outcome) is not dict or outcome.get("operation_ref") != expected:
        raise ContractError(prefix + "action_conflict")
    pending = runtime is None
    if pending:
        if (not isinstance(recovery_context, BindingContext) or recovery_operation_key != operation_key
                or recovery_context.run_id != context.run_id or recovery_context.episode_id != context.episode_id
                or not records._equal(recovery_context.request, context.request)):
            raise ContractError(prefix + "action_conflict")
        actual, _ = authenticate_molecular_invocation(registry, tool_name, arguments, plain(context.scope), operation_key)
        if actual is not recovery_context:
            raise ContractError(prefix + "action_conflict")
    else:
        if type(runtime) is not dict:
            raise ContractError(prefix + "action_conflict")
        if "pending_work_after_action" in runtime:
            validate_pending(runtime["pending_work_after_action"])
        if canonical({key: value for key, value in runtime.items() if key != "pending_work_after_action"}) != row["result"]:
            raise ContractError(prefix + "action_conflict")
    if tool_name in {"result.macs2.peaks", "find_enriched_motifs_with_homer", "identify_transcription_factor_binding_sites",
            "result.variants.vcf", "analyze_protease_kinetics", "analyze_arsenic_speciation_hplc_icpms",
            "predict_protein_disorder_regions", "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations", "generate_gene_embeddings_with_ESM_models"}:
        from gene_annotation_episode.execution_contracts import digest as execution_digest
        request_sha256 = execution_digest(plain(context.request))
    else:
        request_sha256 = hashlib.sha256(canonical(plain(context.request)).encode()).hexdigest()
    invocation = dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
        decision_index=int(suffix), request_sha256=request_sha256,
        scope=plain(context.scope))
    return dict(arguments=json.loads(row["arguments"]), invocation=invocation, outcome=outcome,
        operation_ref=expected, runtime_outcome=runtime, pending_recovery=pending)


def _recorded_molecular_producer_details(registry, source_ref, tool_name, *,
        recovery_context=None, recovery_operation_key=None):
    """Join original producer metadata, with one exact editing-action recovery.

    The old profiles retain their committed-only checks. A NULL runtime outcome
    is usable only for the new editing producer's actual current invocation;
    neither a Source handle nor a supplied recovery key establishes authority.
    """
    from gene_annotation_episode.episodic_workflow.root.communication import plain
    from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
    from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
    _, _, modes, prefix = _publication_profile(tool_name)
    editing = tool_name in {"analyze_cas9_mutation_outcomes", "result.macs2.peaks", "find_enriched_motifs_with_homer",
        "identify_transcription_factor_binding_sites", "result.variants.vcf", "analyze_protease_kinetics",
        "analyze_arsenic_speciation_hplc_icpms", "predict_protein_disorder_regions", "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations",
        "generate_gene_embeddings_with_ESM_models"}
    if ((recovery_context is None) != (recovery_operation_key is None)
            or recovery_context is not None and (not editing or not isinstance(recovery_context, BindingContext))):
        raise ContractError(prefix + "publication_conflict")
    candidates = []
    rows = registry.store.db.execute("""SELECT operation.*,
        action.run_id AS producer_run_id, action.episode_id AS producer_episode_id,
        action.decision_index AS producer_decision_index, action.action AS selected_action,
        action.result AS recorded_outcome
        FROM tool_operations operation JOIN runtime_actions action
          ON (json_extract(action.result,'$.operation_ref')=operation.id
            OR (? AND action.result IS NULL AND operation.operation_key=?
              AND operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index))
        WHERE operation.name=? AND json_extract(operation.result,'$.status') IN ('completed','partial')
          AND EXISTS(SELECT 1 FROM json_each(operation.result,'$.record_refs') published
                     WHERE published.value=?)""",
        (editing and recovery_context is not None, recovery_operation_key, tool_name, source_ref))
    for row in rows:
        arguments = json.loads(row["arguments"])
        if type(arguments) is dict and arguments.get("mode") in modes:
            if tool_name in {"result.macs2.peaks", "find_enriched_motifs_with_homer", "identify_transcription_factor_binding_sites",
                    "analyze_protease_kinetics", "analyze_arsenic_speciation_hplc_icpms",
                    "predict_protein_disorder_regions", "analyze_protein_conservation", "analyze_protein_phylogeny", "detect_and_annotate_somatic_mutations", "generate_gene_embeddings_with_ESM_models"} and source_ref not in json.loads(row["result"]).get("changed_record_refs", []):
                continue  # An unchanged saved window reads its original Source.
            candidates.append((row, arguments))
    if len(candidates) != 1:
        raise ContractError(prefix + "publication_conflict")
    row, arguments = candidates[0]
    records = EpisodeReturnRecords(registry.store, row["producer_run_id"], failure_prefix=prefix)
    producer = records.context(row["producer_episode_id"])
    records.authenticate(producer)
    operation_key = f'{producer.run_id}:{producer.episode_id}:{row["producer_decision_index"]}'
    if editing:
        context = recovery_context if row["recorded_outcome"] is None else producer
        if context is None or not records._equal(context.request, producer.request) or context.path != producer.path:
            raise ContractError(prefix + "publication_conflict")
        details = _recorded_molecular_action_details(registry, context, arguments, operation_key, tool_name,
            recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
        outcome = details["outcome"]
        if (source_ref not in outcome.get("record_refs", []) or type(outcome.get("result")) is not dict
                or outcome["result"].get("source_ref") != source_ref):
            raise ContractError(prefix + "publication_conflict")
        return details
    runtime_outcome = None if row["recorded_outcome"] is None else json.loads(row["recorded_outcome"])
    outcome = json.loads(row["result"])
    if (row["operation_key"] != operation_key
            or row["scope"] != canonical(plain(producer.scope))
            or canonical(json.loads(row["selected_action"])) != canonical(
                dict(kind="tool", tool=tool_name, arguments=arguments))
            or source_ref not in outcome.get("record_refs", [])):
        raise ContractError(prefix + "publication_conflict")
    if (runtime_outcome is None or source_ref not in runtime_outcome.get("record_refs", [])
            or canonical({k: v for k, v in runtime_outcome.items() if k != "pending_work_after_action"}) != row["result"]):
        raise ContractError(prefix + "publication_conflict")
    invocation = dict(run_id=producer.run_id, episode_id=producer.episode_id,
        operation_key=operation_key, decision_index=row["producer_decision_index"],
        request_sha256=hashlib.sha256(canonical(plain(producer.request)).encode()).hexdigest(),
        scope=plain(producer.scope))
    return dict(arguments=arguments, invocation=invocation, outcome=outcome,
        operation_ref=row["id"], runtime_outcome=runtime_outcome, pending_recovery=False)


