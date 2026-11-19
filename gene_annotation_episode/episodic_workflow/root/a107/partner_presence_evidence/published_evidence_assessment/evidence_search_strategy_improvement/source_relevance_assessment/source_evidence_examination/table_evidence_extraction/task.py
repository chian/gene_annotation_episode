"""The task: read the selected table or sheet of the assigned source through the source tools (``source_read``,
``source_locate``) and grade the partner experiment the source reports with the A107 partner graders
(``literature_partner_populate``, ``literature_partner_source_populate``; grader ``partner_requirement``, sheet
``literature_partner_cells``).

Carried from the old ``task.py``, ``task_decision.py``, ``task_instructions.py``, ``task_presentation.py``,
``task_reading_prompt.py``, ``task_action.py``, ``source_operations.py`` and ``source_custody.py``. The old ``report``
tool is gone: the return is the controlled features code reads from the saved sheets, not the model's prose. The
grader prompt (``PARTNER_LEAD`` when partner components are requested, ``PARTNER_TASK``) and the meaning of the sheet
reach the model through the instructions of every decision. One unit is one model-selected tool call. The task always
offers a unit and never ends the Episode: only the yield controller does. The episode has no child and cannot search
or fetch new sources. The other access tools of the old catalogue (state, sequence, archive, workbook, PDF, image
operations) ran through the A107 tool registry, which is not carried (``AXIS_WAVE_BLOCKERS_a107.md``); they are not
offered."""
import json

from jsonschema import ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.scientific_instruction_text import (
    INSTRUCTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_contract_error import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.partner_presence_evidence.partner_population_catalog import (
    POPULATION, grading_instructions, population_tools)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_partner_storage import (
    populate_partner_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.readers.partner_presence_evidence.source_bytes import (
    source_window)
from gene_annotation_episode.episodic_workflow.episode_support.readers.partner_presence_evidence.source_locations import (
    locate, locate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    REF, ContractError, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import read_record_in_scope

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ()

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
# The source tools: descriptions as the tool library states them (old ``_ACCESS_TOOLS``).
SOURCE_TOOLS = [
    {'name': 'source_read',
     'description': 'Read a bounded UTF-8 byte window from an actual source. Choose original for retained source '
                    'bytes, including XML tables/headings omitted by a paragraph projection; text selects that '
                    'projection when available. Explicit stdout/stderr select retained native stream bytes when '
                    'present, without falling back to another representation. Returned artifact/offsets support '
                    'exact anchors.',
     'input_schema': obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE,
                          'representation': {'enum': ['text', 'original', 'stdout', 'stderr']}}, ['source_ref'])},
    {'name': 'source_locate',
     'description': 'Locate an exact supplied literal quote in an explicitly received original or text source '
                    'representation. Return UTF-8 byte witnesses, unchanged neighboring context and bounded match '
                    'continuation. Multiple occurrences remain separate. No normalization, scientific interpretation, '
                    'measurement parsing or evidence credit is performed; no literal match means only no match in the '
                    'examined bytes.',
     'input_schema': locate_schema()},
]
SOURCE_KEYS = {'source_ref', 'data_source_ref', 'sheet_ref', 'metadata_source_ref'}

HISTORY_GUIDANCE = ('Your own earlier read and population outcomes are shown to you as own_literature_outcomes; that '
                    'page creates no new action and does not execute or credit the historical work again.\n')
RETURN_GUIDANCE = ('What returns to your parent is your credit and the features code reads from the partner sheets '
                   'you saved with the partner graders (the partner loss and addback fractions, their status, bounds '
                   'and reasons, the comparison checks, the arm states, condition coverage and spreads); no prose of '
                   'yours is returned. Selecting a tool does not end your work: only the numerical controller does.\n')
TOOL_INSTRUCTION = ('Select one operation per answer: give its name in tool and its operands as JSON text in '
                    'arguments_json. Every operation that names a source must name the assigned source or a source '
                    'derived from it.')


def instructions(partner_requested):
    """The old ``task_instructions.instructions``: the scientific instruction text of the A107 episodes, without the
    spans about actions this episode does not have (reasoning commit, child, report, redelivery, the history
    exchange), then this episode's goal, the partner grader's instructions and the tool instruction."""
    text = replace_span(INSTRUCTIONS, 'Select one ordinary tool, one typed reasoning commitment',
                        'Reasoning owns scientific interpretation', 'Select one ordinary tool at a time. ')
    text = replace_span(text, 'A commissioned child returns ONLY', 'Do not execute native provider tools.',
                        HISTORY_GUIDANCE + RETURN_GUIDANCE)
    return text + '\n' + GOAL + '\n' + grading_instructions(partner_requested) + '\n' + TOOL_INSTRUCTION


def offered():
    """The tools the model is shown: the source tools and the partner graders, by name."""
    return {entry['name']: entry for entry in [*SOURCE_TOOLS, *population_tools()]}


def within_source(store, reference, root, scope):
    """Whether ``reference`` is ``root`` or a source derived from it through ``parent_source_refs`` (the old
    ``_within_source``; each source on the way is read in scope)."""
    pending, seen = [reference], set()
    while pending:
        current = pending.pop()
        if current == root:
            return True
        if current in seen:
            continue
        seen.add(current)
        source = read_record_in_scope(store, current, scope, 'source')
        pending.extend(source.get('parent_source_refs', ()))
    return False


def named_sources(value):
    """Every source reference of a population operation's operands (the old nested ``sources``)."""
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
    """The old ``_tool_arguments``: the arguments against the offered schema, and every source they name against the
    assigned page's source. A violation is a ``ContractError``."""
    validate_schema(arguments, offered()[name]['input_schema'])
    for reference in set(named_sources(arguments)):
        if not store.holds(reference) or not within_source(store, reference, envelope['page_source_ref'],
                                                           envelope['scope']):
            raise ContractError('literature_reading_outside_assigned_source')


def invalid_outcome(ctx, name, arguments, error):
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    field = {'field': error.field} if getattr(error, 'field', None) else {}
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **field, **detail}}


def source_read(arguments, ctx):
    """``source.read`` over the custody-scoped store; an argument or reference the library refuses is an
    ``invalid`` outcome that enters the iterator."""
    envelope, arguments = arguments, arguments['arguments']
    try:
        admitted(ctx.store, 'source_read', arguments, envelope)
        window = source_window(ctx.store, **arguments)
    except (ContractError, ValidationError) as error:
        return invalid_outcome(ctx, 'source_read', arguments, error)
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': window, 'feedback': None}


def source_locate(arguments, ctx):
    """``source.locate`` over the custody-scoped store: the held records are the permitted inputs."""
    envelope, arguments = arguments, arguments['arguments']
    try:
        admitted(ctx.store, 'source_locate', arguments, envelope)
        found = locate(ctx.store, **arguments, permitted_inputs=tuple(ctx.store.refs()), scope=envelope['scope'])
    except (ContractError, ValidationError) as error:
        return invalid_outcome(ctx, 'source_locate', arguments, error)
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': found, 'feedback': None}


def run_population(name, envelope, ctx):
    """One partner grader operation (``literature.partner.populate`` / ``literature.partner.source.populate``): the
    text witnesses are materialized from the held source bytes, the components calculated and the sheet, its cells
    and its assessment saved through ``ctx.store``. Arguments the library refuses are an ``invalid`` outcome with
    their code; the outcome enters the iterator like any other."""
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


def output_schema():
    return {'type': 'object', 'additionalProperties': False, 'required': ['tool', 'arguments_json'],
            'properties': {'tool': {'enum': list(offered())},
                           'arguments_json': {'type': 'string', 'description': 'The operands as one JSON object'}}}


def decide(summary, feedback, ctx):
    """The model chooses one operation, shown the assignment, the custody of the source, its own outcomes, the
    features of the partner sheets it saved, the tools, the measured time and the yield table."""
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'partner_sheets': summary['partner_sheets'],
               'latest_failed_population': summary['literature_selected_population_attempt'],
               'action_yields': summary['action_yields'], 'feedback': feedback,
               'tools': list(offered().values()), 'time_accounting': time_accounting(ctx.clock.progress_time)}
    return ModelRequest('REASONING', instructions(summary['partner_requested']), context, output_schema())


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). An answer that selects no offered tool, or
    operands that are not a JSON object, is invalid; the operands are checked against the tool's schema and the
    assigned source by the tool, as the old ``execute`` did."""
    try:
        name = response['tool']
        if name not in offered():
            raise ValueError('tool_not_offered:' + repr(name))
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
    except (KeyError, TypeError, ValueError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'page_source_ref': summary['literature_assignment']['page']['source_ref']})
