"""MSA/MetaCATS information for the existing API and results commissions.

This module describes caller-bound operations. Enumeration performs no service
probe, preparation, submission, acquisition, parsing or scientific calculation.
Native preparation and numerical result contracts retain their existing owners.
"""
from copy import deepcopy

from .bvbrc_appservice_contracts import contract_schema
from .execution_episodes import RESULTS_SCHEMA


_PROVIDERS = {
    "bvbrc_msa": ("MSA", "msa", (
        "ordinary_alignment", "prealigned_analysis", "segment_alignment",
        "segment_concatenation", "mauve_alignment")),
    "bvbrc_metacats": ("MetaCATS", "metacats", ("files", "groups", "auto")),
}
_RESULT_MODES = {
    "ordinary_alignment": ("ordinary_new_alignment",),
    "prealigned_analysis": ("ordinary_prealigned",),
    "segment_alignment": ("segment_alignment",),
    "segment_concatenation": ("segment_concatenation",),
    "mauve_alignment": ("mauve_first_block_projection", "mauve_blocks"),
    "files": ("files",), "groups": ("groups",), "auto": ("auto",),
}
_DESCRIPTIONS = {
    "ordinary_alignment": (
        "Align supplied DNA or protein sequences with BV-BRC MSA using Muscle or Mafft; "
        "measure aligned positions, gaps, conservation and explicit reference differences."),
    "prealigned_analysis": (
        "Measure gaps, conservation and reference differences in an already acquired "
        "BV-BRC MSA alignment. This entry exposes results analysis; its prealigned launch "
        "bypass is unbound because the retained file-type definition does not establish it."),
    "segment_alignment": (
        "Align explicitly selected genome segments with BV-BRC MSA, retaining separate "
        "segment membership, alignments, reference correspondence and measured differences."),
    "segment_concatenation": (
        "Concatenate explicitly selected genome-segment alignments with BV-BRC MSA, "
        "retaining segment order, gap-filled missing segments and original coordinate maps."),
    "mauve_alignment": (
        "Align supplied DNA with BV-BRC MSA progressiveMauve; retain all XMFA blocks, "
        "native strand/position correspondence and coverage, separately from its first-block FASTA."),
    "files": (
        "Compare alignment-position symbol counts among supplied metadata groups with "
        "BV-BRC MetaCATS, using the supplied aligned FASTA and metadata file."),
    "groups": (
        "Compare alignment-position symbol counts among selected BV-BRC feature groups "
        "with MetaCATS, preserving fetched members, MAFFT alignment and group associations."),
    "auto": (
        "Compare alignment-position symbol counts for explicit feature-to-group entries "
        "with BV-BRC MetaCATS, preserving each requested occurrence and fetched sequence."),
}
_MODE_INSTRUCTIONS = {
    "ordinary_alignment": (
        "Align the supplied DNA or protein sequences using the selected Muscle or Mafft "
        "operation. Supply actual fasta_files, feature_groups, feature_list, genome_list, "
        "select_genomegroup and/or fasta_keyboard_input fields as appropriate; input_type "
        "does not make these independent native input fields mutually exclusive. Keep "
        "their original bindings. A meaningful selected_segments genome request uses the "
        "separate segment entry. The retained ordinary genome branch takes the first "
        "returned contig per genome; it does not establish complete genome coverage. "
        "Original labels may be replaced during alignment and restored afterward; "
        "duplicate labels, fetched sequences and translated inputs require explicit "
        "member/coordinate evidence. Request only the reference, conservation or "
        "correspondence measurements needed for the assigned comparison."),
    "prealigned_analysis": (
        "Analyze the actual supplied or acquired aligned FASTA under the original MSA "
        "task and authenticated content bindings. This entry has a results commission "
        "only. Do not submit a bypass through this entry or relabel a new alignment as "
        "prealigned analysis. The retained producer bypasses alignment for one file "
        "whose type contains aligned, but the retained fasta_files.type enum has only "
        "feature_dna_fasta and feature_protein_fasta. input_status=aligned does not "
        "establish that bypass. A deployed definition and actual accepted parameters "
        "would be needed to bind that launch path. Preserve alignment membership and "
        "the actual original task; supplied supplemental bytes do not create a task."),
    "segment_alignment": (
        "Align each explicitly selected genome segment. Supply genome_list and/or "
        "select_genomegroup plus nonempty genome_selection.selected_segments, alphabet "
        "dna, and Muscle or Mafft. The retained segment branch rejects concurrent "
        "fasta_files, feature_groups, feature_list or pasted sequences and rejects "
        "progressiveMauve. Preserve the actual genome_sequence records, segment tokens, "
        "contigs and row identities; a requested segment list does not prove which "
        "records were fetched. The helper sorts locus names, can suffix duplicate IDs "
        "and emits gap-filled rows for missing member/locus combinations. Missing "
        "segments are not automatically biological absence. Select each per-segment "
        "analysis explicitly, including when the task also requests concatenation. "
        "Missing coordinate evidence leaves original coverage unknown while valid "
        "alignment measurements remain available."),
    "segment_concatenation": (
        "Request the native segment branch with genome_list and/or select_genomegroup, "
        "nonempty genome_selection.selected_segments, alphabet dna, Muscle or Mafft, "
        "and explicit genome_selection.concat_segments=true. Supply no concurrent "
        "file, feature or pasted-sequence inputs. The producer retains per-segment "
        "outputs and additionally writes a concatenated alignment in sorted locus "
        "order, filling a missing member/locus with gaps. Preserve actual segment "
        "order, boundaries, source records, members and transformations; neither a "
        "gap-filled block nor a concatenated row length proves biological absence or "
        "an original sequence denominator. This entry selects the concatenated "
        "analysis. Select the separate segment entry for a per-segment result and "
        "retain the dependence between those views of the same task."),
    "mauve_alignment": (
        "Align the selected DNA with aligner=progressiveMauve and alphabet=dna using "
        "the ordinary MSA input branch, without an active selected-segment request. "
        "Acquire the complete native XMFA. The retained producer writes a separate "
        "FASTA derivative of only the first block and relabels its rows using staged "
        "input-header order; that derivative is not a whole-genome alignment. Select "
        "mauve_blocks for the native document and mauve_first_block_projection for "
        "the derivative; keep their original relationship explicit. The declared "
        "mauve_xmfa_v1 reader preserves all blocks, zero/omitted members, strands and "
        "literal characters. Coordinates distinguish aligned columns, native member "
        "positions, byte-verified staged source records and separately evidenced "
        "original member occurrences. Supply actual source bytes and file/entry/argv "
        "order for source coverage. FASTA and raw DNA source readers are bound; "
        "GenBank and DNAstar source extraction remains unavailable. Choose represented, "
        "multi_member_block or cooccupied_column coverage explicitly. Preserve interval "
        "unions, overlapping placements and denominators; do not add block spans or "
        "infer an original genome map from a native label."),
    "files": (
        "Use input_type=files with the actual alignment_file and group_file, and "
        "alphabet=na or aa. This path stages the supplied alignment and metadata "
        "rather than running MAFFT. Retain complete original FASTA and metadata "
        "bytes, full headers, exact category columns and sequence-to-metadata joins. "
        "The producer passes its files-mode header flag to metadata_parser; declare "
        "the actual metadata layout for extraction. Do not uppercase supplied file "
        "sequences merely because the separate groups and auto branches do so. "
        "Original # symbols and generated masks of leading/trailing dashes require "
        "different provenance, including for all-gap rows."),
    "groups": (
        "Use input_type=groups with the actual nonempty groups list and alphabet=na "
        "or aa. The producer fetches each feature group's members and sequences, "
        "uppercases fetched sequences, creates metadata from each group path and "
        "then runs MAFFT. Preserve original group paths, exact fetched memberships, "
        "sequence occurrences, generated metadata and actual alignment bytes. A "
        "group may have no fetched members; keep that requested provenance without "
        "inventing sequences. Overlapping groups or duplicate identifiers do not "
        "establish independent observations or a unique metadata join. Do not "
        "describe this branch as prealigned file input."),
    "auto": (
        "Use input_type=auto with the ordered auto_groups array and alphabet=na or "
        "aa. Each original entry supplies id and grp; retain optional native metadata "
        "without treating it as a measured result. The producer fetches the requested "
        "feature sequences, uppercases them, creates metadata from those id/grp entries "
        "and runs MAFFT. Preserve each original parameter pointer and exact value, "
        "including repeated feature/group entries, separately from actual fetched "
        "members. A fetched sequence can have a distinct input binding. Missing "
        "retrieval retains the request with an unresolved sequence link; it does not "
        "create a member. Do not silently deduplicate entries or join by taxon/name."),
}
_MSA_INSTRUCTIONS = (
    "Use the native dna/protein alphabet and real selected aligner/strategy; a legacy "
    "ClustalW description or RNA label does not establish a current route. Native "
    "preparation does not inject defaults into the original request. Preserve the "
    "requested and observed settings separately. For ref_type=string, the retained "
    "producer trims outer whitespace and writes ref_string directly into input.fasta "
    "without adding a header; retain its actual FASTA and prove the reference row. "
    "For feature_id, genome_id or first references, retain the actual fetched/selected "
    "row and its identity evidence. A reference label alone cannot prove correspondence. "
    "Acquire the actual aligned FASTA, native .snp.tsv frequency table and consensus "
    "FASTA as distinct artifacts. The table is a column-frequency table, not per-member "
    "variant calls. Native score is distinct from entropy in bits and from separately "
    "calculated reference differences. Preserve terminal gaps, exact denominators and "
    "the native consensus; do not force a consensus when no strict majority exists. "
    "An available FastTree Newick is a separate selected artifact. Its name does not "
    "prove model, support method or units; midpoint rooting is not biological rooting. "
    "Comparisons with organismal relationships need the supplied tree and actual tip "
    "mapping. An alignment or tree alone does not supply a function assignment."
)
_METACATS_INSTRUCTIONS = (
    "Preserve the native p_value cutoff, complete actual alignment and metadata, "
    "adjusted count matrix and raw R outputs when acquired, and native chi-square and "
    "pairwise export tables. The normal upload list does not guarantee original "
    "metadata, adjusted sequences, the count matrix or raw R files; missing operands "
    "remain explicit acquisition requirements. Use the metacats_input_fasta reader "
    "where original # characters must be retained. Biological groups, native group "
    "ordinals, R column tokens and exported labels are different associations. Native "
    "R reproduction requires its actual order evidence; biological grouping does not. "
    "Specify separate biological and native-reproduction requests. Retain raw counts, "
    "pseudocounts, expected counts, chi-square, degrees of freedom, p-values/log tails "
    "and effect components separately. The native pairwise degrees-of-freedom and "
    "underflow conventions must not replace the biological calculation. Native NA, "
    "underflow, measured zero and unavailable remain distinct. The exported p<cutoff "
    "rows do not establish the tested population. Multiplicity needs the complete "
    "eligible family or an explicit supported denominator/assumption. Empty exports "
    "do not prove zero tests. Keep analysis and category identities in each family; "
    "the same category label in two analyses is not an identity join. These statistics "
    "measure the selected association, not a calibrated probability of gene function."
)
_EXECUTION_INSTRUCTIONS = (
    "Where this entry exposes a launch route, commission the existing launch episode "
    "and its selected API child with the original job and constraints. "
    "api.bvbrc_appservice.prepare validates the selected application, parameters, "
    "input bindings and output destination without submitting. Input transfer uses "
    "separately selected workspace_metadata, workspace_create and upload operations "
    "when needed. submit performs the selected primitive AppService.start_app2 call "
    "and retains its actual request, response and task identity. Use the generic "
    "resource monitoring task with selected status/query_tasks and task_info stdout "
    "or stderr observations. Preserve native state, observation time and logs; "
    "process liveness does not establish throughput. The episode chooses further "
    "observations and repairs; there is no fixed polling cadence or automatic retry. "
    "The existing results episode selects task_info, workspace_metadata, list_outputs, "
    "download_capability and download as needed for the original task's actual files. "
    "A filename, HTML report or directory entry does not prove numerical format or "
    "original producer-byte identity. Preparation, transfer and task receipts do not "
    "receive invented annotation-confidence scores. This configured API route does "
    "not establish live authentication, deployment or local/HPC scientific execution."
)
_RESULT_INSTRUCTIONS = (
    "Select exact artifact roles, analysis-local slots, native reader formats and "
    "dialects, populations, calculation requests and the parent's typed return before "
    "acquisition. A bundle role selects the exact original output requirement's role; "
    "do not infer it from a filename. Supply source-backed member/row, feature/genome, "
    "function/taxon, transformation and category associations through scientific_inputs "
    "and supplied_metadata. Additional files need their original supplied_contents "
    "bindings and complete bytes. Source labels inside JSON do not authenticate a "
    "claim. The adapter's native parsers and metadata extractors fill the numerical "
    "sheet; separate deterministic calculators consume that sheet and explicit "
    "parameters. Those functions perform no acquisition, job, resource or model "
    "operation. Use the finite requested_form_schema selectors for the needed native "
    "measurements, calculated components, selected positions/tests and qualifications. "
    "Keep full bytes, associations, sheets and component sets internally, including "
    "valid partial work and unrelated failed analyses. Recalculate saved sheets with "
    "changed explicit parameters without reacquiring data or rewriting historical "
    "observations. Return only the original requested typed facts through the "
    "bvbrc_alignment return sources. No extra model call restates recorded facts; no "
    "full sheet or parent yield history is inserted into the child's instructions."
)


def _nonempty_array():
    return {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}


def _segment_trigger():
    # This is the producer's branch condition, not a substitute input_type.
    return {"required": ["genome_selection"], "properties": {
        "genome_selection": {"type": "object", "required": ["selected_segments"],
            "properties": {"selected_segments": {"type": "array", "minItems": 1}}}},
        "anyOf": [{"required": ["genome_list"]}, {"required": ["select_genomegroup"]}]}


def _native_mode_schema(mode):
    value = {"type": "object", "properties": {}}
    properties = value["properties"]
    if mode in {"files", "groups", "auto"}:
        properties.update(input_type={"const": mode}, alphabet={"enum": ["na", "aa"]})
        value["required"] = ["input_type"]
        if mode == "files":
            value["required"].extend(("alignment_file", "group_file"))
            properties.update({key: {"type": "string", "minLength": 1}
                               for key in ("alignment_file", "group_file")})
        elif mode == "groups":
            value["required"].append("groups")
            properties["groups"] = _nonempty_array()
        else:
            value["required"].append("auto_groups")
            properties["auto_groups"] = {"type": "array", "minItems": 1, "items": {
                "type": "object", "required": ["id", "grp"], "properties": {
                    "id": {"type": "string", "minLength": 1}, "grp": {"type": "string"}}}}
    elif mode == "mauve_alignment":
        properties.update(aligner={"const": "progressiveMauve"}, alphabet={"const": "dna"})
        value.update(required=["aligner"], **{"not": _segment_trigger()})
    else:
        properties["aligner"] = {"enum": ["Muscle", "Mafft"]}
        if mode == "ordinary_alignment":
            value["not"] = _segment_trigger()
        else:
            properties["alphabet"] = {"const": "dna"}
            properties["genome_selection"] = {"type": "object", "required": ["selected_segments"],
                "properties": {"selected_segments": _nonempty_array()}}
            value["required"] = ["genome_selection"]
            value["anyOf"] = [{"required": [field], "properties": {field: _nonempty_array()}}
                              for field in ("genome_list", "select_genomegroup")]
            for field in ("fasta_files", "feature_groups", "feature_list"):
                properties[field] = {"type": "array", "maxItems": 0}
            properties["fasta_keyboard_input"] = {"type": "string", "maxLength": 0}
            if mode == "segment_concatenation":
                segment = properties["genome_selection"]
                segment["required"].append("concat_segments")
                segment["properties"]["concat_segments"] = {"type": "boolean", "const": True}
    return value


def alignment_tool_contracts(*, resource_id: str, assignment_schema: dict,
                             provider: str) -> list[dict]:
    """Declare one configured provider's real mode-specific commission routes."""
    if type(resource_id) is not str or not resource_id.strip() or "\0" in resource_id:
        raise ValueError("alignment_explicit_api_resource_required")
    if not isinstance(assignment_schema, dict):
        raise ValueError("alignment_api_assignment_schema_required")
    if type(provider) is not str or provider not in _PROVIDERS:
        raise ValueError("alignment_provider_invalid")
    from .bvbrc_alignment_bundle_contracts import parameters_schema

    application, schema_provider, modes = _PROVIDERS[provider]
    rows = []
    for mode in modes:
        parameters = deepcopy(parameters_schema(provider=schema_provider))
        parameters.setdefault("allOf", []).append({"properties": {"analyses": {
            "items": {"properties": {"analysis": {"properties": {
                "mode": {"enum": list(_RESULT_MODES[mode])}}}}}}}})
        selector = contract_schema("ResultSelector")
        selector.setdefault("allOf", []).append({"properties": {"adapter": {
            "type": "object", "required": ["adapter_id", "adapter_version", "parameters"],
            "properties": {"adapter_id": {"const": provider}, "adapter_version": {"const": "1"},
                "parameters": parameters}}}})
        results = deepcopy(RESULTS_SCHEMA)
        results["properties"]["selector"] = selector
        schemas, routes = [], []
        if mode != "prealigned_analysis":
            launch = deepcopy(assignment_schema)
            launch.setdefault("allOf", []).append({"properties": {
                "resource_id": {"const": resource_id}, "service": {"const": "bvbrc_appservice"},
                "request": {"properties": {"required_application_id": {"const": application},
                    "parameters": _native_mode_schema(mode)}}}})
            schemas.append(launch)
            routes.append({"entry_role": "launch", "resource_id": resource_id, "resource_role": "launch_api"})
        schemas.append(results)
        routes.append({"entry_role": "results", "resource_id": resource_id, "resource_role": "results"})
        rows.append({"name": "bvbrc." + schema_provider + "." + mode,
            "description": _DESCRIPTIONS[mode], "resources": "api",
            "instructions": " ".join((_MODE_INSTRUCTIONS[mode],
                _MSA_INSTRUCTIONS if schema_provider == "msa" else _METACATS_INSTRUCTIONS,
                _EXECUTION_INSTRUCTIONS, _RESULT_INSTRUCTIONS)),
            "input_schema": {"oneOf": schemas},
            "invocation_route": {"kind": "commission", "routes": routes}})
    return rows


__all__ = ["alignment_tool_contracts"]
