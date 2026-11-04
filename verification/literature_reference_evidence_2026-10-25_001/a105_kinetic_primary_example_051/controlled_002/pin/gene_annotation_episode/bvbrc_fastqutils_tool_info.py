"""FastqUtils information for the existing API launch and results episodes."""
from copy import deepcopy

from .bvbrc_appservice_contracts import contract_schema
from .bvbrc_fastqutils_contracts import _definition_closure
from .execution_episodes import RESULTS_SCHEMA

_INSTRUCTIONS = '''Inspect or preprocess the supplied sequencing reads through the selected BV-BRC FastqUtils service. Supply original paired_end_libs, single_end_libs or srr_libs arrays, the ordered recipe, output_path and output_file. Preserve library order, repeated recipe entries, original spelling and start parameters. A paired library may omit read2; do not infer a mate. Files and internally named inputs are valid starting material; no candidate function or public gene identifier is required.

The available native recipe steps are TRIM, PAIRED_FILTER, FASTQC, ALIGN and SCRUB_HUMAN. Choose only the operations required for the assigned investigation. TRIM changes the current reads. PAIRED_FILTER partitions paired and singleton reads. FASTQC inspects the current population and may reuse a previously recorded QC result. ALIGN produces an alignment branch and requires reference_genome_id. SCRUB_HUMAN produces a cleaned branch. Neither alignment nor cleaning automatically replaces the current read population in the inspected producer. Submitted recipe order is a request, not proof that each step executed. Multiple libraries and repeated steps require exact original-task and artifact associations; never infer them from a basename.

Commission the existing launch episode with the selected job, constraints and requested typed handoff. Its API child selects api.bvbrc_appservice.prepare to validate supplied parameters and the application definition without submission. Explicit input uploads, submission, status and selected log observations remain separate available primitive operations. Submission uses the exact preparation receipt and preserves the native task. Generic API monitoring instructions apply; native states and logs inform the episode's own next choice. There is no fixed retry, polling schedule or hidden resource substitution.

Commission the existing results episode for that original task. Use actual task_info(job_result_id), Workspace metadata, task manifest, exact manifest members, download capabilities and complete selected bytes as needed. The episode chooses those acquisitions. Select bvbrc_fastqutils version2 with analysis_id, documents, metadata_bindings and calculation_requests. Documents may name an existing output requirement before bytes are downloaded; already possessed inputs use their exact content binding. Multiple distinct matching artifacts are ambiguous. A filename suffix is not a format or completeness guarantee. Preserve missing, malformed, partial and unknown observations separately from measured zero.

Declared native formats include FASTQ/plain or gzip, SAM1.6, BAM1/BGZF, FastQC0.12.1 HTML/data/ZIP, Trim Galore0.6.10 reports with embedded Cutadapt4.9 full reports, fastq-pair0.3 stderr and Hostile1.1.0 JSON. Keep each Cutadapt invocation, mate and adapter occurrence distinct. Cutadapt output may be filtered again by Trim Galore; its output count does not establish the final FASTQ count. Adapter-removal events can exceed unique reads. Preserve histogram lengths and error bins, native chance estimates and rounded percentages with their meanings. A reported producer version and the actual grammar are separate evidence; a matching parser cannot establish a deployed version. FastQC graph images cannot supply missing numerical tables. Native smoothed distributions and scaled kmer counts retain those meanings. A BAI index supplies no read denominator. Retained p3-sra run-centric JSON supplies reported total bases, sequencing spots, archive bytes, read length and read types per spot. Preserve each run row and its sample/platform labels. Spots are not reads, and n_reads counts read types or a layout fallback, not total reads. Reported read-length basis and producer version may be unknown; filenames do not establish downloaded-byte or mate relationships. These metadata quantities do not earn an acquisition-confidence score. SAMstat 2.2.3 legacy HTML and 2.5.0 HTML have different native statistics and alignment-flag exclusions. Preserve the actual producer version, reported alignment record populations, mate strata, counts, quality summaries and uncertainty. Legacy embedded arrays retain their coordinate labels, density or clustered-mean meanings and native defects; current SVG plots do not expose their original numerical arrays. Do not reconstruct those arrays from graph geometry. A rounded display remains rounded. A closed HTML report does not establish that all original input records were processed. The recognized FastqUtils SAMstat failure report carries a failed measurement and explicit execution-evidence requirement; it is not a zero-result analysis. Unsupported SAMstat versions, other Cutadapt versions and other SRA formats remain retained artifacts with explicit parser requirements until their formats are implemented.

The sheet retains read and base counts, symbols, lengths, quality histograms, alignment records, native report quantities, populations and exact supplied metadata. Composition uses explicit denominators. Quality-model expected errors require a full histogram and either format-defined SAM/BAM quality or an explicit source-bound FASTQ encoding assumption. Keep that assumption with the result; do not replace it with FastQC's inferred encoding label. Fractions of original input reads require the complete input-read denominator and unambiguous actual read-segment correspondence. A mapped-only BAM cannot supply the total input population. Retention requires compatible before/after counts and a native report relationship or an explicitly recorded lineage assumption. Such an assumption permits conditional arithmetic but never proves recipe completion. Multiple Hostile reports may have overwritten one another in the producer; the final report cannot represent every library.

SAMstat report-bin calculations are separate from original-read mapping. Select samstat_report_mapping_v1 with the report-wide population, one reported mate stratum, or the two explicitly disjoint mate strata from one artifact. They calculate the mapped-record fraction and native MAPQ-at-least-30-bin fraction among those reported alignment records. Keep all four bin counts, numerator, denominator and population qualifications. Do not combine a report-wide total with its mates or sum different reports. MAPQ 255 shares the high native bin but does not establish known mapping confidence. Unknown original-input coverage remains unknown; an explicit prefix remains partial. A zero denominator is undefined, missing bins stay missing, and conflicting counts remain incompatible. Select the numerical components and return fields needed for the assigned question. Deterministic calculators use the saved sheet and explicit parameters without acquiring data or rerunning software. Individual operands, units, numerator, denominator and assumptions remain inspectable. Read counts, Phred-model errors, retention and mapping fractions are not annotation probabilities. Request measurement, component, category, population, association, requirements or request_status facts through the original typed parent form. one_target preserves missing slots; exact_rows retains all actual matches and reports excess cardinality. available_value and typed_state have different missing-value requirements. Only requested facts cross the boundary; full native bytes and sheets remain stored. Parsing, calculation and forwarding add no completed action or credit. This API binding does not establish current service deployment or local/HPC execution.'''


def fastqutils_tool_contracts(*, resource_id: str, assignment_schema: dict) -> list[dict]:
    if type(resource_id) is not str or not resource_id.strip() or '\0' in resource_id:
        raise ValueError('fastqutils_explicit_api_resource_required')
    if type(assignment_schema) is not dict:
        raise ValueError('fastqutils_api_assignment_schema_required')
    text = {'type': 'string', 'minLength': 1}
    platform = {'type': 'string', 'enum': ['infer', 'illumina', 'pacbio', 'pacbio_hifi', 'nanopore']}
    inputs = {
        'paired_end_libs': {'type': 'array', 'items': {'type': 'object', 'required': ['read1'],
            'properties': {'read1': deepcopy(text), 'read2': {'type': ['string', 'null']}, 'platform': deepcopy(platform)}}},
        'single_end_libs': {'type': 'array', 'items': {'type': 'object', 'required': ['read'],
            'properties': {'read': deepcopy(text), 'platform': deepcopy(platform)}}},
        'srr_libs': {'type': 'array', 'items': {'type': 'object', 'required': ['srr_accession'],
            'properties': {'srr_accession': deepcopy(text)}}},
    }
    launch = deepcopy(assignment_schema)
    launch.setdefault('allOf', []).append({'properties': {
        'resource_id': {'const': resource_id}, 'service': {'const': 'bvbrc_appservice'},
        'request': {'properties': {'required_application_id': {'const': 'FastqUtils'},
            'parameters': {'type': 'object', 'required': ['recipe', 'output_path', 'output_file'],
                'properties': {**inputs, 'recipe': {'type': 'array', 'minItems': 1, 'items': deepcopy(text)},
                    'output_path': deepcopy(text), 'output_file': deepcopy(text),
                    'reference_genome_id': {'type': ['string', 'null']}},
                'anyOf': [{'required': [name], 'properties': {name: {'minItems': 1}}} for name in inputs]}}}}})
    selector = contract_schema('ResultSelector')
    selector['$id'] = 'urn:gene-annotation:fastqutils:selector:2'
    parameters = {'$id': 'urn:gene-annotation:fastqutils:parameters:2',
        '$ref': '#/$defs/ProviderParameters', '$defs': _definition_closure('ProviderParameters')}
    selector.setdefault('allOf', []).append({'properties': {
        'endpoint': {'const': 'requested_projection'},
        'adapter': {'type': 'object', 'required': ['adapter_id', 'adapter_version', 'parameters'],
            'properties': {'adapter_id': {'const': 'bvbrc_fastqutils'},
                'adapter_version': {'const': '2'}, 'parameters': parameters}}}})
    results = deepcopy(RESULTS_SCHEMA)
    results['properties']['selector'] = selector
    return [{'name': 'bvbrc.fastqutils',
        'description': 'Inspect, trim, pair, map or clean supplied sequencing reads through BV-BRC; return selected native measurements and explicit numerical components.',
        'resources': 'api', 'instructions': _INSTRUCTIONS,
        'input_schema': {'oneOf': [launch, results]},
        'invocation_route': {'kind': 'commission', 'routes': [
            {'entry_role': 'launch', 'resource_id': resource_id, 'resource_role': 'launch_api'},
            {'entry_role': 'results', 'resource_id': resource_id, 'resource_role': 'results'}]}}]


__all__ = ['fastqutils_tool_contracts']
