"""GeneTree/CodonTree information for existing launch/results commissions.

Enumeration describes caller-bound API work. It performs no discovery,
preparation, submission, acquisition, parsing or calculation. Native request
validation and numerical result contracts keep their existing owners.
"""
from copy import deepcopy

from .bvbrc_appservice_contracts import contract_schema
from .bvbrc_phylogeny_bundle_contracts import parameters_schema
from .execution_episodes import RESULTS_SCHEMA


_PROVIDERS = {
    "bvbrc_gene_tree": ("GeneTree", "gene_tree", (
        "gene_tree", "concatenated_sequence_loci")),
    "bvbrc_codon_tree": ("CodonTree", "codon_tree", (
        "core_genome_codon_protein",)),
}
_DESCRIPTIONS = {
    "gene_tree": (
        "Estimate relationships among supplied gene or sequence-feature members with BV-BRC "
        "GeneTree; retain the selected locus alignment, tree, branch measurements and explicit "
        "function/taxon associations."),
    "concatenated_sequence_loci": (
        "Estimate relationships from explicitly selected concatenated sequence loci with "
        "BV-BRC GeneTree, preserving locus order, member correspondence, missing-locus gaps "
        "and separate per-locus outputs."),
    "core_genome_codon_protein": (
        "Estimate relationships among selected genomes with BV-BRC CodonTree's combined "
        "coding-nucleotide and protein family alignments, retaining family membership, "
        "partitions, native trees and measured selection statistics."),
}
_MODE_INSTRUCTIONS = {
    "gene_tree": (
        "Assign GeneTree the supplied sequence-feature comparison and select each locus "
        "analysis explicitly. The native application produces a tree for each staged locus. "
        "For file inputs, the retained producer derives loci from the basename before its "
        "first dot, tokenizes FASTA headers and can suffix duplicate member labels; retain "
        "the original file/member identities and source-backed transformations. A selected "
        "gene_tree result is a per-locus view even when the same original task also requested "
        "concatenation. It does not by itself establish organismal relationships or a function "
        "assignment. Supply exact function/taxon records and injective tip mappings to an "
        "explicit supplied organismal tree when those comparisons are requested."),
    "concatenated_sequence_loci": (
        "Assign GeneTree explicitly associated sequence loci and set the actual native "
        "request.parameters.genome_selection.concat_segments to true. There is no separate "
        "concatenate launch parameter. The retained producer emits all per-locus analyses "
        "and an additional concatenated analysis. It concatenates sorted staged loci and "
        "fills a missing locus for a retained member with gaps. Keep original file/member "
        "bindings, distinct locus identities, locus order, final block correspondence and "
        "recorded transformations; an all-gap block does not prove biological absence. "
        "Avoid the reserved staged locus name concatenated, which would select that locus "
        "instead of the combined matrix in this producer. The native selected_segments "
        "option concerns genome-group segment retrieval; its requested value alone cannot "
        "prove which segments were returned. Per-locus and concatenated artifacts may "
        "supply distinct analytical views of the same task only with explicit associations. "
        "This named results contract selects concatenated_sequence_loci analyses; preserve "
        "the other outputs and never silently remove an originally selected analysis to "
        "fit it. Original-member coverage needs actual residue maps for each contributing "
        "member, not the concatenated row length as a replacement denominator."),
    "core_genome_codon_protein": (
        "Assign CodonTree the explicit main genome IDs and/or genome groups, selected "
        "number_of_genes, bootstraps, max_genomes_missing and max_allowed_dups, and output "
        "destination. This AppService operation uses the combined coding-nucleotide and "
        "protein path; codon-only, protein-only, Pos3, PLFam and debug/preparation CLI "
        "switches are not bound service modes. Leaves represent genomes; preserve each "
        "feature-to-family-to-genome association and the dependence between protein and "
        "coding-nucleotide representations of the same gene. Keep requested main, requested "
        "optional, source-backed group members, actually forwarded optional, returned, "
        "eligible, evaluated and final populations distinct. The retained App wrapper "
        "writes optional_genome_ids but does not forward its optional input file; a request "
        "cannot establish their use. Group paths and final tips do not supply requested "
        "membership. Missing family matrix cells are unknown unless an explicit complete "
        "population establishes absence. Preserve native paralog exclusions and missing "
        "CDS records without claiming optimal selection or validated translation. Current "
        "combined output uses aligned FASTA; the retained older example uses relaxed "
        "PHYLIP. Acquire the actual matrix, partition file, raw/support/rooted/display trees "
        "as separately selected objects, native membership, family-statistics, genome-count "
        "and analysis-statistics tables and available RAxML 8 logs. Declare the exact "
        "table dialect, including the known missing tab in the current family-statistics "
        "header. Per-family final alignments, bootstrap replicate forests and historical "
        "per-sequence frequency data are not guaranteed normal service outputs. Final "
        "alignment statistics do not reconstruct missing pre-trim/evaluated populations. "
        "The four global codon/protein partitions do not identify family block boundaries. "
        "Mixed-model joint branch lengths are not per-nucleotide divergence or time."),
}
_GENE_INSTRUCTIONS = (
    "Select native GeneTree sequences with explicit source types and alphabet DNA or "
    "Protein; RNA is not in the native enum. The retained producer requires at least four "
    "staged members. Bind actual Workspace files, feature groups, "
    "genome groups or inline feature IDs to their exact request parameter pointers. The "
    "retained feature_ids branch fetches protein sequence even when DNA was requested. "
    "A single declared aligned input bypasses alignment; multiple inputs are aligned "
    "per locus. Native recipes are RAxML, PhyML and FastTree. The inspected producer does "
    "not consume alignment_program or bootstrap as requested controls; it uses MAFFT for "
    "alignment and recipe-specific source defaults. Requested alphabet/model/threads and "
    "bootstrap values remain separate from actual observed settings. Preserve trim and "
    "gap-filter evidence without inventing original coordinates. Acquire complete final "
    "aligned FASTA or, for PhyML, relaxed sequential PHYLIP, and raw Newick plus any "
    "phyloXML derivative. The normal upload list omits separate engine log files even "
    "when produced locally. HTML command/report text is not an implemented log parser. "
    "PhyML/FastTree log measurements remain unavailable unless a supported explicit "
    "reader is supplied; an output filename cannot establish engine/model/support method. "
    "GeneTree XML conversion can insert missing branch lengths as zero and lose zero "
    "support. Preserve XML observations with those qualifications; prefer original "
    "raw Newick for original branch facts. A rooted XML marker is not biological rooting."
)
_EXECUTION_INSTRUCTIONS = (
    "Use the existing launch episode and its selected API child for the unchanged native "
    "assignment. The invocation schema also includes the existing results commission; "
    "its version identifies which assignment is supplied. api.bvbrc_appservice.prepare "
    "validates the selected application definition, original native parameters, inputs "
    "and output destination without submitting. Select workspace_metadata, workspace_create "
    "and upload separately when input preparation or transfer is needed. submit performs "
    "the selected AppService.start_app2 call and retains the actual request, response and "
    "original task identity. Use the resource-generic monitoring episode and selected "
    "status/query_tasks observations plus task_info stdout or stderr when relevant; retain "
    "native states, observation times and actual logs. Logs and process liveness do not "
    "prove productive execution, completion or throughput. Choose further observations "
    "within the episode; no polling cadence or automatic retry is supplied. Results can "
    "select task_info, workspace_metadata, list_outputs, download_capability and download "
    "to obtain the actual original-task artifacts. Retain task, Workspace path/UUID, "
    "manifest/association evidence and complete acquired bytes. A directory entry, HTML "
    "report or filename suffix does not prove format, task production or immutable "
    "producer-byte identity. Transfer/status/preparation facts receive no fabricated "
    "annotation-confidence score. This API route does not claim local scientific "
    "execution, live authentication, deployment or a successfully executed service job."
)
_RESULT_INSTRUCTIONS = (
    "Before results acquisition, select exact semantic roles and analysis-local artifact "
    "slots, reader format/dialect, original source-order tree indices, populations, "
    "calculation parameters and requested typed fields. The scientific mode is stored "
    "at adapter.parameters.analyses[].analysis.mode. A role alone is not proof of which "
    "locus/analysis produced an artifact. Pass exact source-backed input/member, row/tip, "
    "feature/family/genome, function and taxon joins through the originally selected "
    "scientific_inputs and supplied_metadata. Already acquired supplemental native "
    "documents also need their exact original supplied_contents byte bindings; nested "
    "JSON source identifiers do not authenticate them. The bound provider adapter uses "
    "the declared Newick, aligned FASTA, relaxed PHYLIP, RAxML partition, phyloXML, "
    "RAxML 8 log and, for CodonTree, native-table readers. Separate provider extractors "
    "populate the numerical sheet, and calculate_gene_tree or calculate_codon_tree "
    "computes the explicit selected components without network, job or model calls. "
    "Use the provider requested_form_schema finite selectors for numerical counts, "
    "gap/conservation/site measurements, branch/support rows, function composition, "
    "relationship comparisons and, for CodonTree, family measurements/membership; "
    "request requirements and qualifications when the receiver needs them. Known "
    "branch units, support methods, bootstrap denominators and original residue maps "
    "require actual evidence. Missing, not measured, failed, truncated, incompatible "
    "and measured zero remain distinct. Preserve valid independent partial data and "
    "signed native values. Branch support and native conservation/selection statistics "
    "are not calibrated annotation probabilities. Retain every originally selected "
    "analysis, complete native artifact, populated sheet, parameter set and component "
    "set internally. Recalculate saved sheets with explicit changed parameters without "
    "reacquiring data or rerunning analysis; historical observations remain unchanged. "
    "Return only the parent's originally requested typed numerical fields through the "
    "existing bvbrc_phylogeny return sources, with no model-composed restatement or "
    "automatic widening of that form."
)


def phylogeny_tool_contracts(*, resource_id: str, assignment_schema: dict,
                            provider: str) -> list[dict]:
    """Describe one bound provider's real launch and mode-specific result routes."""
    if type(resource_id) is not str or not resource_id or "\0" in resource_id:
        raise ValueError("phylogeny_explicit_api_resource_required")
    if not isinstance(assignment_schema, dict):
        raise ValueError("phylogeny_api_assignment_schema_required")
    if type(provider) is not str or provider not in _PROVIDERS:
        raise ValueError("phylogeny_provider_invalid")
    application, schema_provider, modes = _PROVIDERS[provider]
    rows = []
    for mode in modes:
        launch = deepcopy(assignment_schema)
        request = {"properties": {"required_application_id": {"const": application}}}
        if mode == "concatenated_sequence_loci":
            request["properties"]["parameters"] = {
                "type": "object", "required": ["genome_selection"], "properties": {
                    "genome_selection": {"type": "object", "required": ["concat_segments"],
                        "properties": {"concat_segments": {"type": "boolean", "const": True}}}}}
        launch.setdefault("allOf", []).append({"properties": {
            "resource_id": {"const": resource_id}, "service": {"const": "bvbrc_appservice"},
            "request": request}})
        parameters = parameters_schema(provider=schema_provider)
        parameters["$id"] = "urn:gene-annotation:phylogeny:parameters:" + mode
        parameters["properties"]["analyses"]["items"]["properties"]["analysis"]["properties"]["mode"] = {"const": mode}
        selector = contract_schema("ResultSelector")
        selector["$id"] = "urn:gene-annotation:phylogeny:selector:" + mode
        selector["allOf"] = [{"properties": {"adapter": {"type": "object", "properties": {
            "adapter_id": {"const": provider}, "adapter_version": {"const": "1"},
            "parameters": parameters}, "required": ["adapter_id", "adapter_version", "parameters"]}}}]
        results = deepcopy(RESULTS_SCHEMA)
        results["properties"]["selector"] = selector
        instructions = [_MODE_INSTRUCTIONS[mode]]
        if schema_provider == "gene_tree":
            instructions.append(_GENE_INSTRUCTIONS)
        instructions.extend((_EXECUTION_INSTRUCTIONS, _RESULT_INSTRUCTIONS))
        rows.append({"name": "bvbrc." + schema_provider + "." + mode,
            "description": _DESCRIPTIONS[mode], "resources": "api",
            "instructions": " ".join(instructions),
            "input_schema": {"oneOf": [launch, results]},
            "invocation_route": {"kind": "commission", "routes": [
                {"entry_role": "launch", "resource_id": resource_id, "resource_role": "launch_api"},
                {"entry_role": "results", "resource_id": resource_id, "resource_role": "results"}]}})
    return rows


__all__ = ["phylogeny_tool_contracts"]
