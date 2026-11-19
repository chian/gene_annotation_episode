"""The task: the model examines the one assigned source. It reads it through the source tools, grades a partner
experiment it reports with the A107 partner graders (``literature_partner_populate``,
``literature_partner_source_populate``; grader ``partner_requirement``, sheet ``literature_partner_cells``), or
commissions a table, ordered-reading or targeted-passage investigation of it. The task always offers a unit and never
ends the Episode: its yield controller does. The episode has no acquisition tools (no search, no public read).

Old files carried here: task_instructions (instruction text), task_presentation and task_reading_prompt (the
TASK/STEERING prompt), task_decision (what a decision contains), task_action (admission of an answer),
source_operations (the tool catalogue, its argument validation and execution), source_custody (the source ancestry
rule) and the ``_CHILDREN`` and ``_ROLE_INSTRUCTIONS`` of contracts.py (the three children and their descriptions).
Not carried: the ``redeliver_report`` action, the ``request_context`` exchange, the old runner's checkpoint and
suspension, and the prose ``report_finding`` tool (the return is the controlled features of the partner sheets). The
grader prompt and the sheet's meaning reach the model through the instructions of every decision. The other access
tools of the old catalogue ran through the A107 tool registry, which is not carried (``AXIS_WAVE_BLOCKERS_a107.md``);
they are not offered."""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.scientific_instruction_text import INSTRUCTIONS
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_contract_error import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.partner_presence_evidence.partner_population_catalog import (
    POPULATION, grading_instructions, population_tools)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_partner_storage import (
    populate_partner_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import rejection_feedback
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import decode_strict_output, strict_output_schema
from gene_annotation_episode.episodic_workflow.episode_support.readers.partner_presence_evidence.source_bytes import (
    source_window)
from gene_annotation_episode.episodic_workflow.episode_support.readers.partner_presence_evidence.source_locations import (
    locate, locate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    REF, ContractError, identity, obj, validate_schema)

from .goal import GOAL

_BASE = ('partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
         'source_relevance_assessment/source_evidence_examination/')
# The three children by the old role names (the old ``_CHILDREN['literature_page']``).
CHILD_SLOTS = {'literature_table': _BASE + 'table_evidence_extraction',
               'literature_ordered': _BASE + 'source_coverage_improvement',
               'literature_targeted': _BASE + 'passage_evidence_extraction'}
SERVICES = ()

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}
REPRESENTATION = {'enum': ['text', 'original', 'stdout', 'stderr']}
SOURCE_TOOLS = [
    {'name': 'source_read',
     'description': 'Read a bounded UTF-8 byte window from an actual source. Choose original for retained source '
                    'bytes, including XML tables/headings omitted by a paragraph projection; text selects that '
                    'projection when available. Explicit stdout/stderr select retained native stream bytes when '
                    'present, without falling back to another representation. Returned artifact/offsets support '
                    'exact anchors.',
     'input_schema': obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE, 'representation': REPRESENTATION},
                         ['source_ref'])},
    {'name': 'source_locate',
     'description': 'Locate an exact supplied literal quote in an explicitly received original or text source '
                    'representation. Return UTF-8 byte witnesses, unchanged neighboring context and bounded match '
                    'continuation. Multiple occurrences remain separate. No normalization, scientific interpretation, '
                    'measurement parsing or evidence credit is performed; no literal match means only no match in the '
                    'examined bytes.',
     'input_schema': locate_schema()},
]
SOURCE_KEYS = {'source_ref', 'data_source_ref', 'sheet_ref', 'metadata_source_ref'}
WINDOW = obj({'source_ref': REF, 'representation': REPRESENTATION, 'offset': INTEGER, 'limit': POSITIVE})
TABLE = obj({
    'source_ref': REF, 'sheet_key': TEXT, 'offset': INTEGER, 'limit': INTEGER, 'header_row': POSITIVE,
    'where': obj({'column': {'type': 'string', 'pattern': '^[A-Z]+$'}, 'match': {'enum': ['equals', 'contains']},
                  'value': TEXT, 'case_sensitive': {'type': 'boolean'}}, ['match', 'value', 'case_sensitive'])},
    ['source_ref', 'sheet_key', 'offset', 'limit'])
# The old ``_ROLE_INSTRUCTIONS`` of the three child roles, with what each child's selection is.
CHILD_OPTIONS = {
    'literature_table':
        'Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and '
        'footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches '
        'keep their native identity. Article XML tables are read through exact original-source windows. Selection: '
        'a table selection (source_ref, sheet_key, offset, limit, optional header_row and where) or a byte window to '
        'begin reading at.',
    'literature_ordered':
        'Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte '
        'continuations and retain representation identity. Decide whether to continue, reread, change the examined '
        'window or interpret obtained evidence from actual outcomes. Selection: the byte window to begin reading at '
        '(source_ref, representation, offset, limit).',
    'literature_targeted':
        'Investigate the supplied source-bound passages for the assigned question. Read neighboring context, '
        'qualifications or alternative passages as needed and revise the interpretation from actual outcomes. '
        'Separate spans remain separate; never concatenate them into a fabricated quotation. Selection: spans, one or '
        'more byte windows (source_ref, representation, offset, limit).',
}
CHILD_GUIDANCE = ('You may commission a table, ordered-reading or targeted-passage investigation of this source '
                  'with a child selection; it returns its credit and the controlled features of the partner sheets '
                  'it saved, which you receive among received child reports.')
RETURN_GUIDANCE = ('What returns to your parent is your credit and the features code reads from the partner sheets '
                   'you and your children saved; no prose of yours is returned. Selecting a tool or a child does not '
                   'end your work: only the numerical controller does.')
STEERING = ('Select the received source_ref, artifact_ref and zero-based half-open UTF-8 byte range for text '
            'witnesses. Preserve the exact observed subject, source meaning and unresolved target correspondence.')


def instructions(partner_requested):
    """The old composed instructions: the shared investigation text, this episode's own goal text, the partner
    grader's instructions and the child and return guidance. The spans of the shared text about the report form,
    redelivery and the old history tool describe actions that no longer exist."""
    text = replace_span(INSTRUCTIONS, 'A commissioned child returns ONLY', 'On a fresh provider conversation,', '')
    text = replace_span(text, 'On a fresh provider conversation,', 'Do not execute native provider tools.',
                        'Your own earlier outcomes are in own_literature_outcomes of the context.\n')
    return '\n'.join((text, GOAL, grading_instructions(partner_requested), CHILD_GUIDANCE, RETURN_GUIDANCE))


def offered():
    return {entry['name']: entry for entry in [*SOURCE_TOOLS, *population_tools()]}


def child_selections(page):
    """The child selections for this page: every window and table names the page's own source, and every window the
    page's representation (each child reads exactly that page; the commission is the parent's to get right)."""
    source = {'const': page['source_ref']}
    window = obj({'source_ref': source, 'representation': {'const': page['representation']}, 'offset': INTEGER,
                  'limit': POSITIVE})
    table = {**TABLE, 'properties': {**TABLE['properties'], 'source_ref': source}}
    return {'literature_table': {'anyOf': [table, window]}, 'literature_ordered': window,
            'literature_targeted': obj({'spans': {'type': 'array', 'minItems': 1, 'items': window}})}


def action_schema(page):
    """What the model answers with: one tool and its operands as JSON text, or one child and its selection (the old
    action kinds ``tool`` and ``child``)."""
    branches = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments_json'],
                 'properties': {'kind': {'const': 'tool'}, 'tool': {'enum': list(offered())},
                                'arguments_json': {'type': 'string',
                                                   'description': 'The operands as one JSON object'}}}]
    branches.extend({'type': 'object', 'additionalProperties': False, 'required': ['kind', 'slot', 'arguments'],
                     'properties': {'kind': {'const': 'child'}, 'slot': {'const': slot},
                                    'arguments': obj({'selection': child_selections(page)[slot]})}}
                    for slot in CHILD_SLOTS)
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': branches}}}


def transport(schema):
    return strict_output_schema(schema, open_records_as_text=False,
                                argument_transport_error='a107_argument_transport_not_carried')


def section(parts, title, value):
    if value not in (None, [], {}, ()):
        parts.extend(('', title, json.dumps(value, sort_keys=True, allow_nan=False)))


def render_prompt(summary, feedback):
    """The old TASK and STEERING layout of ``render_literature_experimental_prompt``."""
    parts = ['TASK']
    section(parts, 'Assigned question', GOAL)
    section(parts, 'Assigned scope', summary['scope'])
    section(parts, 'Parent assignment and selected source operands',
            {'page': summary['page'], 'partner_components': summary['partner_components']})
    section(parts, 'Representations available for selected sources', summary['source_custody'])
    section(parts, 'Available selected operations', list(offered().values()))
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
    return ModelRequest('REASONING', instructions(summary['partner_components'] is not None),
                        {'prompt': render_prompt(summary, feedback)}, transport(action_schema(summary['page'])))


def action(response, summary, records, ctx):
    schema = action_schema(summary['page'])
    try:
        decoded = decode_strict_output(response, transport(schema), open_records_as_text=False,
                                       argument_transport_error='a107_argument_transport_not_carried')
        Draft202012Validator(schema).validate(decoded)
        selection = decoded['selection']
        if selection['kind'] == 'child':
            return ChildCall(selection['slot'], selection['arguments'])
        arguments = json.loads(selection['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
    except (ValidationError, ValueError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(selection['tool'], {'arguments': arguments, 'scope': summary['scope'],
                                        'page_source_ref': summary['page']['source_ref']})


def within_source(store, reference, root):
    """The old ``_within_source``: the source descends from the assigned page source (``parent_source_refs``)."""
    pending, seen = [reference], set()
    while pending:
        current = pending.pop()
        if current == root:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(store.get(current).get('parent_source_refs', ()))
    return False


def named_sources(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in SOURCE_KEYS and isinstance(child, str):
                yield child
            else:
                yield from named_sources(child)
    elif isinstance(value, list):
        for child in value:
            yield from named_sources(child)


def admitted(store, name, arguments, envelope):
    """The old ``_tool_arguments`` rule: the arguments fit the tool's schema and every source they name is held and
    lies within the assigned page source. A violation is a ``ContractError``."""
    validate_schema(arguments, offered()[name]['input_schema'])
    for reference in set(named_sources(arguments)):
        if not store.holds(reference) or not within_source(store, reference, envelope['page_source_ref']):
            raise ContractError('literature_reading_outside_assigned_source')


def invalid_outcome(ctx, name, arguments, error):
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    field = {'field': error.field} if getattr(error, 'field', None) else {}
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **field, **detail}}


def source_read(arguments, ctx):
    envelope, arguments = arguments, arguments['arguments']
    try:
        admitted(ctx.store, 'source_read', arguments, envelope)
        window = source_window(ctx.store, **arguments)
    except (ContractError, ValidationError) as error:
        return invalid_outcome(ctx, 'source_read', arguments, error)
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': window, 'feedback': None}


def source_locate(arguments, ctx):
    envelope, arguments = arguments, arguments['arguments']
    try:
        admitted(ctx.store, 'source_locate', arguments, envelope)
        found = locate(ctx.store, **arguments, permitted_inputs=tuple(ctx.store.refs()), scope=envelope['scope'])
    except (ContractError, ValidationError) as error:
        return invalid_outcome(ctx, 'source_locate', arguments, error)
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': found, 'feedback': None}


def run_population(name, envelope, ctx):
    """One partner grader operation: text witnesses materialized from the held source bytes, the components
    calculated and the sheet, its cells and its assessment saved through ``ctx.store``. Arguments the library refuses
    are an ``invalid`` outcome with their code; the outcome enters the iterator like any other."""
    arguments = envelope['arguments']
    try:
        admitted(ctx.store, name, arguments, envelope)
        return populate_partner_sheet(ctx.store, envelope['scope'], envelope['page_source_ref'], arguments,
                                      ctx.operation_key)
    except (ContractError, ExperimentalContractError, ValidationError) as error:
        return invalid_outcome(ctx, POPULATION[name], arguments, error)


def literature_partner_populate(arguments, ctx):
    return run_population('literature_partner_populate', arguments, ctx)


def literature_partner_source_populate(arguments, ctx):
    return run_population('literature_partner_source_populate', arguments, ctx)


TOOLS = {'source_read': source_read, 'source_locate': source_locate,
         'literature_partner_populate': literature_partner_populate,
         'literature_partner_source_populate': literature_partner_source_populate}
