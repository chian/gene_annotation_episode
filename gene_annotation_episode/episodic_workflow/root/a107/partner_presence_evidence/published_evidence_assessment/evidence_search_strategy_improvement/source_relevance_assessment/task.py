"""The task: the model decides which of the located sources merit examination. It searches and reads through the
access and acquisition tools, grades partner experiments with the A107 partner graders (sheet ``literature_partner_cells``)
and commissions a source examination for one selected source. The task always offers a unit and never ends the
Episode: its yield controller does. The prose ``report_finding`` tool is not carried: the return is the controlled
features of the partner sheets.

Old files carried here: task_instructions (instruction text), task_presentation and task_reading_prompt (the
TASK/STEERING prompt), task_decision (what a decision contains), task_action (admission of an answer),
source_operations (the tool catalogue, its argument validation and execution), source_custody (the artifact of a
representation) and the ``_CHILDREN``, ``_ROLE_INSTRUCTIONS``, ``_PAGE`` and tool lists of contracts.py.
Not carried: the ``redeliver_report`` action, the ``request_context`` exchange, the saved-exchange checks, the
checkpoint and the suspension (old runner). The access and acquisition tools are the library's ``ToolRegistry`` of the
axis, handed ``ctx.store``; it is still written against the raw Store (see the blocked file).

The old assignment named no ``page``, so the old confinement of every tool source to the page's source did not apply
to this episode and is not carried."""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.scientific_instruction_text import INSTRUCTIONS
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_contract_error import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.partner_presence_evidence.partner_population_catalog import grading_instructions, population_catalog_entries
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_partner_storage import populate_partner_sheet
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import rejection_feedback
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import decode_strict_output, strict_output_schema
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError, REF, identity, obj, source_location_inputs, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

_BASE = ('partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
         'source_relevance_assessment/')
# The one child by the old role name (the old ``_CHILDREN['literature_search']``).
CHILD_SLOTS = {'literature_page': _BASE + 'source_evidence_examination'}
SERVICES = ('tool_catalog', 'public_clients')

# The tools of the old catalogue, by the name the model selects (the library's name); the episode's own tool
# names cannot contain a dot.
ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references',
                'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract',
                'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page',
                'execution.estimate')
ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset')
POPULATION_TOOLS = ('literature.partner.populate', 'literature.partner.source.populate')
PERMITTED_RECORD_TOOLS = ('source.locate', 'source.sequence.scan', 'source.sequence.references',
                          'source.experimental.records')
PROPOSAL_ERRORS = (ContractError, CustodyError, ValueError, KeyError, TypeError)

REFERENCES = {'type': 'array', 'items': REF, 'uniqueItems': True}
REPRESENTATION = {'type': 'string', 'enum': ['text', 'original', 'stdout', 'stderr']}
# What the model supplies to commission the child: the page (old ``_PAGE``, ``page_assignment_v1``). The scope, the
# finding unit and the records passed are this episode's own.
PAGE = obj({'version': {'const': 'page_assignment_v1'}, 'source_ref': REF, 'representation': REPRESENTATION,
            'artifact_ref': REF, 'question_context_refs': REFERENCES, 'prior_delivery_refs': REFERENCES})
CHILD_SELECTIONS = {'literature_page': PAGE}
# The old ``_ROLE_INSTRUCTIONS`` of the child role, with what its selection is.
CHILD_OPTIONS = {
    'literature_page':
        'Investigate where and how this exact source should be examined. Choose ordinary source operations or '
        'selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit '
        'some XML headings, tables and footnotes; retained original bytes remain addressable. Selection: the page '
        'assignment (version page_assignment_v1, source_ref, representation, artifact_ref, question_context_refs, '
        'prior_delivery_refs) of one held source.',
}
CHILD_GUIDANCE = ('You may commission an examination of one selected source with a page selection; its credit and '
                  'the controlled features of its partner sheets return to you among received child reports.')
RETURN_GUIDANCE = ('What returns to your parent is your credit and the features code reads from the partner sheets you '
                   'and your child saved; no prose of yours is returned. Selecting a tool or a child does not end '
                   'your work: only the numerical controller does.')
STEERING = ('Select the received source_ref, artifact_ref and zero-based half-open UTF-8 byte range for text '
            'witnesses. Preserve the exact observed subject, source meaning and unresolved target correspondence.')


def instructions(partner_requested):
    """The old composed instructions: the shared investigation text and this episode's own goal text. The spans of
    the shared text about redelivery and the old history tool describe actions that no longer exist; the old texts
    for reasoning commits and waiting were not added for this role, and the pending-child redelivery text describes
    the removed redelivery action."""
    text = replace_span(INSTRUCTIONS, 'A commissioned child returns ONLY',
                        'On a fresh provider conversation,', '')
    text = replace_span(text, 'On a fresh provider conversation,', 'Do not execute native provider tools.',
                        'Your own earlier outcomes are in own_literature_outcomes of the context.\n')
    return '\n'.join((text, GOAL, grading_instructions(partner_requested), CHILD_GUIDANCE, RETURN_GUIDANCE))


def population_catalog():
    """The A107 partner grader operations (old ``partner_source_contracts.population_catalog_entries()``)."""
    return list(population_catalog_entries())


def offered_catalog(entries):
    """The old ``catalog``: the access and acquisition tools of the registry, with the ncbi and estimate narrowing,
    then the partner population operations, every input schema exposing source locations."""
    allowed = (*ACCESS_TOOLS, *ACQUISITION_TOOLS)
    result = []
    for entry in entries:
        if entry['name'] not in allowed:
            continue
        entry = json.loads(json.dumps(entry))
        if entry['name'] == 'public.ncbi.search':
            entry['input_schema']['properties']['database'] = {'enum': ['pubmed']}
        if entry['name'] == 'execution.estimate':
            branches = [branch for branch in entry['input_schema'].get('anyOf', ())
                        if branch.get('properties', {}).get('tool', {}).get('const') in {'source.xlsx.sheets',
                                                                                         'source.xlsx.rows'}]
            if not branches:
                continue
            entry['input_schema'] = {'anyOf': branches}
        result.append(entry)
    result.extend(population_catalog())
    return [{**entry, 'input_schema': source_location_inputs(entry['input_schema'])} for entry in result]


def action_schema(catalog):
    """What the model answers with: one tool and its arguments, or one child and its selection (the old action
    kinds ``tool`` and ``child``)."""
    branches = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'],
                 'properties': {'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                                'arguments': entry['input_schema']}} for entry in catalog]
    branches.extend({'type': 'object', 'additionalProperties': False, 'required': ['kind', 'slot', 'arguments'],
                     'properties': {'kind': {'const': 'child'}, 'slot': {'const': slot},
                                    'arguments': obj({'selection': CHILD_SELECTIONS[slot]})}}
                    for slot in CHILD_SLOTS)
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': branches}}}


def transport(schema):
    return strict_output_schema(schema, open_records_as_text=False,
                                argument_transport_error='a107_argument_transport_not_carried')


def section(parts, title, value):
    if value not in (None, [], {}, ()):
        parts.extend(('', title, json.dumps(value, sort_keys=True, allow_nan=False)))


def render_prompt(summary, catalog, feedback):
    """The old TASK and STEERING layout of ``render_literature_experimental_prompt``. Its fixed paragraphs
    (``lead``, source availability, source scope, component reading task) are in the library module
    ``literature_source_presentation``, which was not placed: they are not reproduced here."""
    parts = ['TASK']
    section(parts, 'Assigned question', GOAL)
    section(parts, 'Assigned scope', summary['scope'])
    section(parts, 'Parent assignment and selected source operands',
            {'question_context_refs': summary['question_context_refs'],
             'search_result_refs': summary['search_result_refs'], 'partner_components': summary['partner_components']})
    section(parts, 'Representations available for selected sources', summary['source_custody'])
    section(parts, 'Available selected operations', catalog)
    section(parts, 'Permitted narrower investigations', CHILD_OPTIONS)
    steering = ['STEERING', '', STEERING]
    section(steering, 'Own action yields', summary.get('yield_table'))
    section(steering, 'Current partner sheets', {'sheets': summary['partner_sheets'],
                                                 'agreement': summary['partner_agreement']})
    section(steering, 'Received child reports', summary['child_reports'])
    section(steering, 'Own earlier outcomes', {'meaning': summary['literature_history_meaning'],
                                               'page': summary['own_literature_outcomes']})
    section(steering, 'Feedback on your last answer', feedback)
    return '\n'.join(parts) + '\n\n' + '\n'.join(steering)


def decide(summary, feedback, ctx):
    catalog = offered_catalog(ctx.services['tool_catalog'].read('entries'))
    return ModelRequest('REASONING', instructions(summary['partner_components'] is not None), {'prompt': render_prompt(summary, catalog, feedback)},
                        transport(action_schema(catalog)))


def named_references(value):
    """Every record a model-written value names: a value under a key ``ref`` or ``..._ref``, or in a list under
    ``..._refs``."""
    if isinstance(value, dict):
        for key, child in value.items():
            if (key == 'ref' or key.endswith('_ref')) and isinstance(child, str):
                yield child
            elif key.endswith('_refs') and isinstance(child, list):
                yield from (item for item in child if isinstance(item, str))
            else:
                yield from named_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from named_references(child)


def artifact_of(source, representation):
    """The old ``_artifact``: the source's artifact for a representation."""
    if representation == 'original':
        return source['artifact_ref']
    if representation == 'text':
        return source.get('text_ref') or source['artifact_ref']
    return source.get(representation + '_ref')


def check_page(records, page):
    """The old validation of the model's page selection (``_validate_page``): the records it names are held and the
    artifact is the source's artifact for the representation. This is the validation of a model answer about this
    episode's own child call, not a check of a commission."""
    for reference in named_references(page):
        if not records.holds(reference):
            raise ContractError('literature_reference_unavailable', detail={'reference': reference})
    if artifact_of(records.get(page['source_ref']), page['representation']) != page['artifact_ref']:
        raise ContractError('literature_source_artifact_mismatch',
                            detail={'reference': page['source_ref'], 'artifact_ref': page['artifact_ref'],
                                    'representation': page['representation']})


def action(response, summary, records, ctx):
    catalog = offered_catalog(ctx.services['tool_catalog'].read('entries'))
    schema = action_schema(catalog)
    try:
        decoded = decode_strict_output(response, transport(schema), open_records_as_text=False,
                                       argument_transport_error='a107_argument_transport_not_carried')
        Draft202012Validator(schema).validate(decoded)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    selection = decoded['selection']
    try:
        if selection['kind'] == 'child':
            check_page(records, selection['arguments']['selection'])
            return ChildCall(selection['slot'], selection['arguments'])
        tool, arguments = selection['tool'], selection['arguments']
        for reference in named_references(arguments):
            if not records.holds(reference):
                raise ContractError('literature_reference_unavailable', detail={'reference': reference})
    except PROPOSAL_ERRORS as error:
        raise Rejected(rejection_feedback(error, category='arguments_or_reference'))
    permitted = list(records.refs()) if tool in PERMITTED_RECORD_TOOLS else None
    return ToolCall(tool.replace('.', '_'), {'tool': tool, 'arguments': arguments, 'scope': summary['scope'],
                                             'permitted_record_refs': permitted})


async def run_registry(arguments, ctx):
    """One operation of the axis registry, handed the custody-scoped store. The registry is the library's old
    ``ToolRegistry(store, ...)`` (raw Store, ``tool_operations`` table, ``store.db``): called as written."""
    registry = ToolRegistry(ctx.store, clients=ctx.services['public_clients'], **ctx.settings['tool_registry'])
    try:
        return await registry.execute_async(arguments['tool'], arguments['arguments'], scope=arguments['scope'],
                                            operation_key=ctx.operation_key,
                                            permitted_record_refs=arguments['permitted_record_refs'])
    except (ContractError, CustodyError) as error:
        return failure_outcome(ctx.store, error, category='arguments_or_reference', cause_code=str(error))


def populate(arguments, ctx):
    """One A107 partner grader operation (``literature.partner.populate`` / ``literature.partner.source.populate``):
    the arguments against the operation's schema, the text witnesses materialized from the held source bytes, the
    eight components calculated and the sheet, its cells and its assessment saved through ``ctx.store``
    (``literature_partner_storage.populate_partner_sheet``; this episode reads no assigned page). Arguments the
    library refuses are an ``invalid`` outcome with their code; the outcome enters the iterator like any other."""
    operation, selected = arguments['tool'], arguments['arguments']
    entries = {entry['name']: entry for entry in population_catalog()}
    try:
        validate_schema(selected, source_location_inputs(entries[operation]['input_schema']))
        return populate_partner_sheet(ctx.store, arguments['scope'], None, selected, ctx.operation_key)
    except (ContractError, ExperimentalContractError, ValidationError) as error:
        detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
        field = {'field': error.field} if getattr(error, 'field', None) else {}
        return {'status': 'invalid',
                'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': operation,
                                                        'arguments': selected}),
                'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error), **field, **detail}}


async def state_query(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_read(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_locate(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_sequence_scan(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_experimental_records(arguments, ctx):
    return await run_registry(arguments, ctx)


async def image_view(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_archive_members(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_archive_extract(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_xlsx_sheets(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_xlsx_rows(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_pdf_info(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_pdf_text(arguments, ctx):
    return await run_registry(arguments, ctx)


async def source_pdf_page(arguments, ctx):
    return await run_registry(arguments, ctx)


async def execution_estimate(arguments, ctx):
    return await run_registry(arguments, ctx)


async def public_literature_search(arguments, ctx):
    return await run_registry(arguments, ctx)


async def public_literature_read(arguments, ctx):
    return await run_registry(arguments, ctx)


async def public_literature_sequence_identity(arguments, ctx):
    return await run_registry(arguments, ctx)


async def public_ncbi_search(arguments, ctx):
    return await run_registry(arguments, ctx)


async def public_pmc_versions(arguments, ctx):
    return await run_registry(arguments, ctx)


async def public_pmc_files(arguments, ctx):
    return await run_registry(arguments, ctx)


async def public_pmc_asset(arguments, ctx):
    return await run_registry(arguments, ctx)


def literature_partner_populate(arguments, ctx):
    return populate(arguments, ctx)


def literature_partner_source_populate(arguments, ctx):
    return populate(arguments, ctx)


TOOLS = {'state_query': state_query,
         'source_read': source_read,
         'source_locate': source_locate,
         'source_sequence_scan': source_sequence_scan,
         'source_sequence_references': source_sequence_references,
         'source_experimental_records': source_experimental_records,
         'image_view': image_view,
         'source_archive_members': source_archive_members,
         'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets,
         'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info,
         'source_pdf_text': source_pdf_text,
         'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate,
         'public_literature_search': public_literature_search,
         'public_literature_read': public_literature_read,
         'public_literature_sequence_identity': public_literature_sequence_identity,
         'public_ncbi_search': public_ncbi_search,
         'public_pmc_versions': public_pmc_versions,
         'public_pmc_files': public_pmc_files,
         'public_pmc_asset': public_pmc_asset,
         'literature_partner_populate': literature_partner_populate,
         'literature_partner_source_populate': literature_partner_source_populate}
