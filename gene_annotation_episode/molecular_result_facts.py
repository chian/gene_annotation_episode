"""Finite Source-owned molecular facts from saved actions and typed returns.

Live groups use the existing publication reader. Frozen and received groups
authenticate original forms and receipt prefixes without reopening their Files.
DTO validation alone confers neither publication authority nor File access.
"""
from collections.abc import Mapping
from copy import deepcopy
import json

from .domain import ContractError, canonical


_PROFILES = {
    "somatic_variant_outcomes": ("detect_and_annotate_somatic_mutations", "somatic_variant_"),
    "esm_gene_embedding_outcomes": ("generate_gene_embeddings_with_ESM_models", "esm_gene_embedding_"),
    "protein_conservation_outcomes": ("analyze_protein_conservation", "protein_conservation_"),
    "protein_phylogeny_outcomes": ("analyze_protein_phylogeny", "protein_phylogeny_"),
    "vcf_result_outcomes": ("result.variants.vcf", "vcf_result_"),
    "itc_binding_parameters": ("analyze_itc_binding_thermodynamics", "itc_parameter_"),
    "liftover_point_mappings": ("liftover_coordinates", "liftover_point_"),
    "circular_dichroism_summaries": ("analyze_circular_dichroism_spectra", "circular_dichroism_"),
    "orf_measurements": ("annotate_open_reading_frames", "ordinary_orf_"),
    "n_glycosylation_motif_outcomes": ("find_n_glycosylation_motifs", "ordinary_n_glycosylation_"),
    "o_glycosylation_hotspot_outcomes": ("predict_o_glycosylation_hotspots", "ordinary_o_glycosylation_"),
    "reference_edit_outcomes": ("analyze_cas9_mutation_outcomes", "reference_edit_outcome_"),
    "macs2_peak_outcomes": ("result.macs2.peaks", "macs2_peak_"),
    "homer_motif_outcomes": ("find_enriched_motifs_with_homer", "homer_motif_"),
    "tf_binding_outcomes": ("identify_transcription_factor_binding_sites", "tf_binding_"),
    "protease_kinetics_outcomes": ("analyze_protease_kinetics", "protease_kinetics_"),
    "arsenic_speciation_outcomes": ("analyze_arsenic_speciation_hplc_icpms", "arsenic_speciation_"),
    "protein_disorder_outcomes": ("predict_protein_disorder_regions", "protein_disorder_"),
    "primer_placement_outcomes": ("align_sequences", "primer_placement_"),
}


def _profile(fact_source):
    try:
        return _PROFILES[fact_source]
    except (KeyError, TypeError) as error:
        raise ContractError("molecular_fact_source_invalid") from error


def _sources(fact_source):
    _profile(fact_source)
    if fact_source == "somatic_variant_outcomes":
        from .somatic_variant_contracts import somatic_fact_sources
        return somatic_fact_sources()
    if fact_source == "esm_gene_embedding_outcomes":
        from .esm_gene_embedding_contracts import esm_gene_embedding_fact_sources
        return esm_gene_embedding_fact_sources()
    if fact_source == "protein_phylogeny_outcomes":
        from .protein_phylogeny_result_contracts import phylogeny_fact_sources
        return phylogeny_fact_sources()
    if fact_source == "protein_conservation_outcomes":
        from .protein_conservation_result_contracts import conservation_fact_sources
        return conservation_fact_sources()
    if fact_source == "primer_placement_outcomes":
        from .primer_placement_result_contracts import ordinary_primer_placement_fact_sources
        return ordinary_primer_placement_fact_sources()
    if fact_source == "protein_disorder_outcomes":
        from .protein_disorder_result_contracts import ordinary_disorder_fact_sources
        return ordinary_disorder_fact_sources()
    if fact_source == "arsenic_speciation_outcomes":
        from .arsenic_speciation_result_contracts import ordinary_arsenic_fact_sources
        return ordinary_arsenic_fact_sources()
    if fact_source == "protease_kinetics_outcomes":
        from .protease_kinetics_result_contracts import ordinary_protease_kinetics_fact_sources
        return ordinary_protease_kinetics_fact_sources()
    if fact_source == "vcf_result_outcomes":
        from .vcf_result_tools import vcf_result_fact_sources
        return vcf_result_fact_sources()
    if fact_source == "tf_binding_outcomes":
        from .tf_binding_result_contracts import tf_binding_fact_sources
        return tf_binding_fact_sources()
    if fact_source == "homer_motif_outcomes":
        from .homer_motif_result_contracts import homer_motif_fact_sources
        return homer_motif_fact_sources()
    if fact_source == "macs2_peak_outcomes":
        from .macs2_peak_result_contracts import macs2_peak_fact_sources
        return macs2_peak_fact_sources()
    if fact_source == "reference_edit_outcomes":
        from .reference_edit_outcome_tools import reference_edit_outcome_fact_sources
        return reference_edit_outcome_fact_sources()
    if fact_source == "orf_measurements":
        from .molecular_sequence_result_contracts import ordinary_orf_fact_sources
        return ordinary_orf_fact_sources()
    if fact_source in {"n_glycosylation_motif_outcomes", "o_glycosylation_hotspot_outcomes"}:
        from .molecular_sequence_result_contracts import ordinary_molecular_sequence_fact_sources
        return ordinary_molecular_sequence_fact_sources(_profile(fact_source)[0])
    if fact_source == "itc_binding_parameters":
        from .molecular_measurement_tools import itc_parameter_fact_sources
        return itc_parameter_fact_sources()
    if fact_source == "circular_dichroism_summaries":
        from .circular_dichroism_contracts import circular_dichroism_fact_sources
        return circular_dichroism_fact_sources()
    from .liftover_contracts import liftover_fact_sources
    return liftover_fact_sources()


def molecular_fact_sources():
    """Declare the finite complete Source-group contracts."""
    return {name: _sources(name)[name] for name in _PROFILES}


def requested_molecular_fact_sources(schema):
    """Unrelated historical forms do not enter the new validation path."""
    properties = schema.get("properties", {}) if isinstance(schema, Mapping) else {}
    if not isinstance(properties, Mapping):
        return ()
    present = {node.get("x-source") for node in properties.values()
        if isinstance(node, Mapping) and isinstance(node.get("x-source"), str)}
    return tuple(name for name in _PROFILES if name in present
        and requested_molecular_fact_fields(schema, fact_source=name))


def requested_molecular_fact_fields(schema, *, fact_source):
    """A requested group retains its exact complete registered schema."""
    _, prefix = _profile(fact_source)
    properties = schema.get("properties", {}) if isinstance(schema, Mapping) else {}
    if not isinstance(properties, Mapping) or not any(isinstance(node, Mapping)
            and node.get("x-source") == fact_source for node in properties.values()):
        return []
    from .communication import plain, validate_closed_schema
    schema = validate_closed_schema(plain(schema))
    available = _sources(fact_source)[fact_source]["report_schema"]
    fields = []
    for name, node in schema["properties"].items():
        if node.get("x-source") == fact_source:
            if canonical(node) != canonical(available):
                raise ContractError(prefix + "requested_schema_conflict")
            fields.append(name)
    return fields


def validate_molecular_fact(value, *, fact_source):
    """Validate the finite DTO; saved-value/provenance checks remain separate."""
    _, prefix = _profile(fact_source)
    if fact_source == "somatic_variant_outcomes":
        from .somatic_variant_contracts import validate_somatic_return
        from .communication import plain
        try:
            return validate_somatic_return(plain(value))
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "protein_phylogeny_outcomes":
        from .protein_phylogeny_result_contracts import validate_phylogeny_return
        from .communication import plain
        try:
            return validate_phylogeny_return(plain(value))
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "esm_gene_embedding_outcomes":
        from .esm_gene_embedding_contracts import validate_esm_embedding_return
        from .communication import plain
        try:
            return validate_esm_embedding_return(plain(value))
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "protein_conservation_outcomes":
        from .protein_conservation_result_contracts import validate_conservation_return
        from .communication import plain
        try:
            return validate_conservation_return(plain(value))
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "primer_placement_outcomes":
        from .primer_placement_result_contracts import validate_ordinary_primer_placement_return
        try:
            return validate_ordinary_primer_placement_return(value)
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "protein_disorder_outcomes":
        from .protein_disorder_result_contracts import validate_ordinary_disorder_return
        try:
            return validate_ordinary_disorder_return(value)
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "arsenic_speciation_outcomes":
        from .arsenic_speciation_result_contracts import validate_ordinary_arsenic_return
        try:
            return validate_ordinary_arsenic_return(value)
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "protease_kinetics_outcomes":
        from .protease_kinetics_result_contracts import validate_ordinary_protease_kinetics_return
        try:
            return validate_ordinary_protease_kinetics_return(value)
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "vcf_result_outcomes":
        from .vcf_result_measurements import validate_vcf_return
        try:
            return validate_vcf_return(value)
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "tf_binding_outcomes":
        from .tf_binding_result_contracts import validate_tf_binding_return
        try:
            return validate_tf_binding_return(value)
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "homer_motif_outcomes":
        from .homer_motif_result_contracts import validate_homer_motif_return
        try:
            return validate_homer_motif_return(value)
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "macs2_peak_outcomes":
        from .macs2_peak_result_contracts import validate_macs2_peak_return
        try:
            return validate_macs2_peak_return(value)
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "reference_edit_outcomes":
        from .reference_edit_outcomes import validate_reference_edit_outcome_return
        try:
            return validate_reference_edit_outcome_return(value)
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "orf_measurements":
        from .molecular_sequence_result_contracts import validate_ordinary_orf_return
        try:
            return validate_ordinary_orf_return(value)
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source in {"n_glycosylation_motif_outcomes", "o_glycosylation_hotspot_outcomes"}:
        from .molecular_sequence_result_contracts import validate_ordinary_molecular_sequence_return
        try:
            return validate_ordinary_molecular_sequence_return(value, operation=_profile(fact_source)[0])
        except ValueError as error:
            raise ContractError(prefix + "return_invalid") from error
    if fact_source == "itc_binding_parameters":
        from .molecular_measurement_tools import validate_itc_parameter_return
        return validate_itc_parameter_return(value)
    if fact_source == "circular_dichroism_summaries":
        from .circular_dichroism_contracts import validate_circular_dichroism_return
        return validate_circular_dichroism_return(value)
    from jsonschema import Draft202012Validator, validators
    from . import liftover_contracts as core
    value = core._copy(value)
    strict = validators.extend(Draft202012Validator, type_checker=
        Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _checker, item: type(item) is int))
    schema = core.liftover_fact_sources()[fact_source]["report_schema"]["items"]
    if not strict(schema).is_valid(value):
        raise ContractError(prefix + "return_invalid")
    references = (value["source_ref"], value["chain"]["source_ref"])
    if any(reference is not None and core._SOURCE.fullmatch(reference) is None for reference in references):
        raise ContractError(prefix + "return_source_invalid")
    return value


def merge_molecular_facts(*groups, fact_source):
    """Deduplicate equal complete Source groups; conflicting copies fail."""
    _, prefix = _profile(fact_source)
    result, seen = [], {}
    for group in groups:
        if type(group) is not list:
            raise ContractError(prefix + "facts_array_required")
        for item in group:
            value = validate_molecular_fact(item, fact_source=fact_source)
            reference, body = value["source_ref"], canonical(value)
            if fact_source in {"orf_measurements", "n_glycosylation_motif_outcomes", "o_glycosylation_hotspot_outcomes",
                    "protease_kinetics_outcomes", "arsenic_speciation_outcomes", "protein_disorder_outcomes", "primer_placement_outcomes", "protein_conservation_outcomes", "protein_phylogeny_outcomes", "esm_gene_embedding_outcomes", "somatic_variant_outcomes"}:
                reference = (reference, canonical(value["selection"]))
            if reference in seen and seen[reference] != body:
                raise ContractError(prefix + "facts_source_conflict")
            if reference not in seen:
                result.append(value)
                seen[reference] = body
    return result


def _project(stored, source_ref, fact_source):
    if fact_source in {"orf_measurements", "n_glycosylation_motif_outcomes", "o_glycosylation_hotspot_outcomes", "reference_edit_outcomes", "macs2_peak_outcomes", "homer_motif_outcomes",
            "tf_binding_outcomes", "vcf_result_outcomes", "protease_kinetics_outcomes", "arsenic_speciation_outcomes", "protein_disorder_outcomes", "primer_placement_outcomes", "protein_conservation_outcomes", "protein_phylogeny_outcomes", "esm_gene_embedding_outcomes", "somatic_variant_outcomes"}:
        value = validate_molecular_fact(stored, fact_source=fact_source)
        if value["source_ref"] != source_ref:
            raise ContractError(_profile(fact_source)[1] + "fact_source_conflict")
        return value
    if fact_source == "itc_binding_parameters":
        from .molecular_measurement_tools import project_itc_parameter_return
        return project_itc_parameter_return(stored, source_ref=source_ref)
    if fact_source == "circular_dichroism_summaries":
        from .circular_dichroism_contracts import project_circular_dichroism_return
        return project_circular_dichroism_return(stored, source_ref=source_ref)
    from .liftover_contracts import project_liftover_return
    return project_liftover_return(stored["components"], source_ref=source_ref)


def own_molecular_facts(registry, context, *, read_received, fact_source):
    """Authenticate current own actions, then project their original Sources."""
    from .communication import plain
    from .episode_return_records import EpisodeReturnRecords
    from .molecular_measurement_tools import read_retained_molecular_publication
    tool_name, prefix = _profile(fact_source)
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix=prefix).authenticate(context)
    if context.role != "scientific_process":
        raise ContractError(prefix + "scientific_owner_required")
    result = []
    rows = registry.store.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? "
        "AND episode_id=? AND json_extract(action,'$.kind')='tool' AND json_extract(action,'$.tool')=? "
        "AND json_extract(result,'$.status') IN ('completed','partial') ORDER BY decision_index",
        (context.run_id, context.episode_id, tool_name))
    for row in rows:
        action, actual = json.loads(row["action"]), json.loads(row["result"])
        key = f'{context.run_id}:{context.episode_id}:{row["decision_index"]}'
        operation = registry.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
        if (operation is None or operation["name"] != tool_name
                or operation["arguments"] != canonical(action["arguments"])
                or operation["scope"] != canonical(plain(context.scope))
                or operation["id"] != actual.get("operation_ref")
                or canonical({k: v for k, v in actual.items() if k != "pending_work_after_action"}) != operation["result"]):
            raise ContractError(prefix + "action_conflict")
        if fact_source == "orf_measurements":
            value = registry.molecular_sequence_results_for(context.run_id).read_ordinary_orf_action_result(
                context, action["arguments"], key, read_received=read_received)
            if (value["source_ref"] not in actual.get("record_refs", [])
                    or canonical(value) != canonical(actual.get("result"))):
                raise ContractError(prefix + "action_source_conflict")
            result.append(_project(value, value["source_ref"], fact_source))
            continue
        if fact_source in {"n_glycosylation_motif_outcomes", "o_glycosylation_hotspot_outcomes", "primer_placement_outcomes"}:
            value = registry.molecular_sequence_results_for(context.run_id).read_ordinary_molecular_sequence_action_result(
                context, action["arguments"], key, operation=tool_name, read_received=read_received)
            if (value["source_ref"] not in actual.get("record_refs", [])
                    or canonical(value) != canonical(actual.get("result"))):
                raise ContractError(prefix + "action_source_conflict")
            result.append(_project(value, value["source_ref"], fact_source))
            continue
        if fact_source == "reference_edit_outcomes":
            from .reference_edit_outcome_tools import read_reference_edit_outcome_action_result
            value = read_reference_edit_outcome_action_result(registry, context,
                action["arguments"], key, reader=read_received)
            if (value["source_ref"] not in actual.get("record_refs", [])
                    or canonical(value) != canonical(actual.get("result"))):
                raise ContractError(prefix + "action_source_conflict")
            result.append(_project(value, value["source_ref"], fact_source))
            continue
        if fact_source == "vcf_result_outcomes":
            from .vcf_result_tools import read_vcf_result_action_result
            value = read_vcf_result_action_result(registry, context,
                action["arguments"], key, reader=read_received)
            if (value["source_ref"] not in actual.get("record_refs", [])
                    or canonical(value) != canonical(actual.get("result"))):
                raise ContractError(prefix + "action_source_conflict")
            result.append(_project(value, value["source_ref"], fact_source))
            continue
        if fact_source == "macs2_peak_outcomes":
            from .macs2_peak_tools import read_macs2_peak_action_result
            value = read_macs2_peak_action_result(registry, context,
                action["arguments"], key, reader=read_received)
            if (value["source_ref"] not in actual.get("record_refs", [])
                    or canonical(value) != canonical(actual.get("result"))):
                raise ContractError(prefix + "action_source_conflict")
            result.append(_project(value, value["source_ref"], fact_source))
            continue
        if fact_source in {"homer_motif_outcomes", "tf_binding_outcomes", "protease_kinetics_outcomes", "arsenic_speciation_outcomes", "protein_disorder_outcomes", "protein_conservation_outcomes", "protein_phylogeny_outcomes", "esm_gene_embedding_outcomes", "somatic_variant_outcomes"}:
            if fact_source == "somatic_variant_outcomes":
                from .somatic_variant_publication import read_somatic_variant_action_result as read_action_result
            elif fact_source == "esm_gene_embedding_outcomes":
                from .esm_gene_embedding_publication import read_esm_gene_embedding_action_result as read_action_result
            elif fact_source == "protein_phylogeny_outcomes":
                from .protein_phylogeny_publication import read_protein_phylogeny_action_result as read_action_result
            elif fact_source == "protein_conservation_outcomes":
                from .protein_conservation_publication import read_protein_conservation_action_result as read_action_result
            elif fact_source == "protein_disorder_outcomes":
                from .protein_disorder_tools import read_protein_disorder_action_result as read_action_result
            elif fact_source == "arsenic_speciation_outcomes":
                from .arsenic_speciation_tools import read_arsenic_speciation_action_result as read_action_result
            elif fact_source == "protease_kinetics_outcomes":
                from .protease_kinetics_tools import read_protease_kinetics_action_result as read_action_result
            elif fact_source == "tf_binding_outcomes":
                from .tf_binding_tools import read_tf_binding_action_result as read_action_result
            else:
                from .homer_motif_tools import read_homer_action_result as read_action_result
            value = read_action_result(registry, context,
                action["arguments"], key, reader=read_received)
            if (value["source_ref"] not in actual.get("record_refs", [])
                    or canonical(value) != canonical(actual.get("result"))):
                raise ContractError(prefix + "action_source_conflict")
            if fact_source == "arsenic_speciation_outcomes" and action["arguments"]["mode"] == "read_inputs":
                # The action reader authenticated the finite supplied-input
                # view. Inspection creates no new numerical result group.
                continue
            result.append(_project(value, value["source_ref"], fact_source))
            continue
        for reference in actual.get("record_refs", []):
            source = registry.store.get(reference)
            if source.get("record_type") != "source" or source.get("provider") != tool_name:
                continue
            publication = read_retained_molecular_publication(registry, context, read_received,
                reference, tool_name=tool_name)
            required = (reference,)
            if fact_source == "itc_binding_parameters":
                required += (publication["received_input"]["file"]["artifact_ref"], publication["grading_ref"])
            if not all(ref in actual["record_refs"] for ref in required):
                raise ContractError(prefix + "action_files_conflict")
            arguments = action["arguments"]
            saved_modes = (("read_stored",) if tool_name == "analyze_itc_binding_thermodynamics"
                else ("read_stored", "calculate_saved"))
            if arguments["mode"] in saved_modes:
                if arguments["result_ref"] != reference:
                    raise ContractError(prefix + "action_source_conflict")
            elif publication["control"]["request"]["invocation"]["operation_key"] != key:
                raise ContractError(prefix + "action_source_conflict")
            result.append(_project(publication["stored"], reference, fact_source))
    return merge_molecular_facts(result, fact_source=fact_source)


def frozen_molecular_facts(store, run_id, context, *, fact_source):
    """Read a literal frozen group; absence remains unknown, not empty."""
    from .episode_return_records import EpisodeReturnRecords
    _, prefix = _profile(fact_source)
    EpisodeReturnRecords(store, run_id, failure_prefix=prefix).authenticate(context)
    row = store.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
        (run_id, context.episode_id)).fetchone()
    if row is None:
        return None
    facts = json.loads(row["facts"])
    if fact_source not in facts:
        return None
    values = facts[fact_source]
    if type(values) is not list:
        raise ContractError(prefix + "frozen_source_invalid")
    for value in values:
        validate_molecular_fact(value, fact_source=fact_source)
    return deepcopy(values)


def validate_frozen_molecular_return(form, schema, frozen, *, fact_source):
    """Compare original typed values without native or private File reads."""
    from .communication import ReportBoundaryError, plain
    _, prefix = _profile(fact_source)
    for name in requested_molecular_fact_fields(schema, fact_source=fact_source):
        actual = plain(form).get(name)
        try:
            if type(frozen) is not list or type(actual) is not list:
                raise ContractError(prefix + "frozen_source_unavailable")
            for item in [*actual, *frozen]:
                validate_molecular_fact(item, fact_source=fact_source)
            if canonical(actual) != canonical(frozen):
                raise ContractError(prefix + "frozen_source_mismatch")
        except ValueError as error:
            message = {
                "itc_binding_parameters": "Return differs from the retained ITC parameter facts",
                "liftover_point_mappings": "Return differs from the retained liftover mapping facts",
                "circular_dichroism_summaries": "Return differs from the retained CD summary facts",
                "orf_measurements": "Return differs from the retained ORF measurement facts",
                "n_glycosylation_motif_outcomes": "Return differs from the retained N-glycosylation motif facts",
                "o_glycosylation_hotspot_outcomes": "Return differs from the retained O-glycosylation hotspot facts",
                "reference_edit_outcomes": "Return differs from the retained reference editing outcome facts",
                "macs2_peak_outcomes": "Return differs from the retained native peak measurement facts",
                "homer_motif_outcomes": "Return differs from the retained native HOMER motif measurement facts",
                "tf_binding_outcomes": "Return differs from the retained native TF score measurement facts",
                "protease_kinetics_outcomes": "Return differs from the retained protease kinetics measurement facts",
                "arsenic_speciation_outcomes": "Return differs from the retained arsenic speciation measurement facts",
                "protein_disorder_outcomes": "Return differs from the retained protein disorder measurement facts",
                "protein_conservation_outcomes": "Return differs from the retained literal conservation facts",
                "protein_phylogeny_outcomes": "Return differs from the retained native phylogeny facts",
                "somatic_variant_outcomes": "Return differs from the retained native somatic variant facts",
                "esm_gene_embedding_outcomes": "Return differs from the retained ESM representation facts",
                "primer_placement_outcomes": "Return differs from the retained primer placement facts",
                "vcf_result_outcomes": "Return differs from the retained VCF result facts",
            }[fact_source]
            raise ReportBoundaryError(message, code=str(error), field=name) from error


def received_molecular_facts(store, run_id, context, *, fact_source):
    """Consume authenticated child forms and original ancestor prefixes."""
    from .episode_receipts import EpisodeReceipts
    from .episode_return_records import EpisodeReturnRecords
    from .execution_contracts import digest
    from .molecular_reference_privacy import molecular_reference_restriction
    tool_name, failure_prefix = _profile(fact_source)
    records = EpisodeReturnRecords(store, run_id, failure_prefix=failure_prefix)
    records.authenticate(context)
    groups, current, prefix, seen = [], context, None, set()
    while True:
        if current.episode_id in seen:
            raise ContractError(failure_prefix + "receipt_lineage_cycle")
        seen.add(current.episode_id)
        if prefix is None:
            attempts = [dict(row) for row in store.db.execute("SELECT decision_index,delivery_ref,child_episode_id,"
                "contract,form FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
                "AND failure IS NULL AND form IS NOT NULL ORDER BY decision_index", (run_id, current.episode_id))]
        else:
            attempts = []
            for frozen in prefix["attempts"]:
                row = store.db.execute("SELECT decision_index,delivery_ref,child_episode_id,contract,form,failure "
                    "FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
                    (run_id, current.episode_id, frozen["decision_index"])).fetchone()
                if (row is None or row["failure"] is not None or row["form"] is None
                        or any(row[name] != frozen[name] for name in ("delivery_ref", "child_episode_id"))
                        or digest(json.loads(row["contract"])) != frozen["contract_sha256"]
                        or digest(json.loads(row["form"])) != frozen["form_sha256"]):
                    raise ContractError(failure_prefix + "received_prefix_conflict")
                attempts.append(dict(row))
        for attempt in attempts:
            schema = json.loads(attempt["contract"])["measurements"]["schema"]
            fields = requested_molecular_fact_fields(schema, fact_source=fact_source)
            if not fields:
                continue
            _, form, authenticated_schema = records._attempt(current, attempt["decision_index"])
            if canonical(schema) != canonical(authenticated_schema):
                raise ContractError(failure_prefix + "received_schema_conflict")
            for name in fields:
                group = form[name]
                if type(group) is not list:
                    raise ContractError(failure_prefix + "received_array_required")
                for value in group:
                    validate_molecular_fact(value, fact_source=fact_source)
                    if molecular_reference_restriction(store, context, value["source_ref"], "source",
                            providers=(tool_name,)) is not True:
                        raise ContractError(failure_prefix + "received_source_not_granted")
                groups.append(group)
        manifest = EpisodeReceipts.read_manifest(store.db, run_id, current.episode_id)
        parent = manifest["parent_episode_id"]
        if parent is None:
            break
        if "received_report_prefix" not in manifest:
            raise ContractError(failure_prefix + "received_prefix_unavailable")
        prefix = manifest["received_report_prefix"]
        parent_context = records.context(parent)
        if current.path[:-1] != parent_context.path:
            raise ContractError(failure_prefix + "received_lineage_conflict")
        current = parent_context
    return merge_molecular_facts(*groups, fact_source=fact_source)


__all__ = ["molecular_fact_sources", "requested_molecular_fact_sources", "requested_molecular_fact_fields",
    "validate_molecular_fact", "merge_molecular_facts", "own_molecular_facts", "frozen_molecular_facts",
    "received_molecular_facts", "validate_frozen_molecular_return"]
