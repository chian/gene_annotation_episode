"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (the
service, the request or job identity, the submission outcome, whether the original usable handoff was
established), the handoff records (returned in custody) and whether the assignment has verified endpoint
information. Every recorded fact source is a selectable field the parent names in ``msg_to_child``; a field name is
the fact-source name with dots written as underscores (a field name cannot contain a dot). The fact-source
declarations come from the library's views of this axis; a source the service did not report is empty."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_and_context_sources.uniprot_return_contracts import (
    uniprot_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.partner_presence_evidence.hmmer_preparation_result_views import (
    preparation_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.partner_presence_evidence.sequence_masking_result_views import (
    masking_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.blast_pairwise_result_views import (
    native_blast_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.blast_utility_result_views import (
    blast_utility_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.hmmer_native_result_views import (
    native_hmmer_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.native_blast_database_result_views import (
    native_blast_database_fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.partner_presence_evidence.native_blast_standard_database_result_views import (
    standard_blast_database_fact_sources)

FINDING_FORM = RecordForm({
    'service': Field('text', 'The API service the work was carried out through'),
    'resource_id': Field('text', 'The bound API resource'),
    'handoff_established': Field('boolean', 'Whether the requested usable original handoff was established'),
    'qualification': Field('text', 'What the recorded service facts establish about the handoff and the submission'),
    'submission_outcome': Field('text', 'The recorded submission outcome, when a service reported one',
                                required=False),
    'request_identity': Field('text', 'The actual request identity, when a service reported one', required=False),
    'job_identity': Field('text', 'The actual job identity, when a service reported one', required=False),
})

# The fact sources, by recorded source name, from the library views that declare them.
SOURCES = {}
for _declare in (native_hmmer_fact_sources, masking_fact_sources, blast_utility_fact_sources,
                 uniprot_fact_sources, standard_blast_database_fact_sources, native_blast_database_fact_sources,
                 preparation_fact_sources, native_blast_fact_sources):
    SOURCES.update(_declare())
EMPTY = {'list': [], 'record_refs': []}


def field_name(source):
    return source.replace('.', '_')


def _declared(spec):
    kind = spec['type']
    items = (spec.get('report_schema') or {}).get('items') or {}
    if kind == 'array':
        kind = 'record_refs' if items.get('format') == 'reference' else 'list'
    return Field(kind, spec['meaning'], required=False)


SOURCES = {source: spec for source, spec in SOURCES.items() if spec['type'] == 'array'}
FIELDS = {field_name(source): _declared(spec) for source, spec in SOURCES.items()}
FIELD_SOURCE = {field_name(source): source for source in SOURCES}
FIXED = {
    'execution_blast_pairwise_result_refs': 'Qualified BLAST pairwise result records of this episode',
    'bvbrc_appservice_support_refs': 'Actually received AppService preparation, Workspace, upload or observation '
                                     'receipts; these are not scientific result acquisitions.',
    'execution_result_refs': 'Qualified actual requested result acquisitions available to this episode.',
}
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the API submission established', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources actually available to this '
                                    'episode; a failed attempt does not establish a successful endpoint.'),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information. '
                                 'Yielding alone is false.'),
    **{name: Field('record_refs', meaning, required=False) for name, meaning in FIXED.items()},
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results; an empty record '
                                     'when no qualified retained data exists.',
                                     required=False),
    'execution_blast_hsps': Field('list', 'Optional explicitly requested native measurements for all published '
                                  'HSPs of this acquired result. No ranking, top-N or significance filter.',
                                  required=False),
    **FIELDS,
})


def final_to_parent(summary, completion, selection):
    finding = {'service': summary['service'], 'resource_id': summary['resource_id'],
               'handoff_established': summary['handoff_established'],
               'qualification': ('original usable handoff established from recorded service facts'
                                 if summary['handoff_established'] else
                                 'original handoff not established; a missing reply does not establish that no job '
                                 'was created')}
    for name in ('submission_outcome', 'request_identity', 'job_identity'):
        if summary[name] is not None:
            finding[name] = summary[name]
    result = {'credit': completion['credit'], 'finding': finding, 'execution_handoff_refs': summary['handoff_refs'],
              'execution_completed': summary['execution_completed']}
    for name in selection:
        if name == 'execution_result_refs':
            result[name] = summary['result_refs']
        elif name == 'execution_result_origin':
            result[name] = {}
        elif name == 'execution_blast_hsps':
            result[name] = summary['facts'].get(name, [])
        elif name in ('execution_blast_pairwise_result_refs', 'bvbrc_appservice_support_refs'):
            result[name] = summary['facts'].get(name, [])
        else:
            result[name] = summary['facts'].get(FIELD_SOURCE[name], EMPTY[FIELDS[name].type])
    return result
