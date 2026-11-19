"""The tools of the library probe: library functions of ``tools/`` and ``readers/`` called on the scoped store."""
import hashlib
import json
from pathlib import Path

from episode_runtime import ToolCall
from episode_runtime.tests.probe.task import SOURCE

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.readers.protein_structure.protein_structure_operands import (
    retained_protein_structure_bytes)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sample_context_evidence.source_bytes import source_window
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.received_sequence_reader import (
    component_chunks)
from gene_annotation_episode.episodic_workflow.episode_support.tools.protein_structure.protein_structure_tools import (
    _stage_retained, _staging)
from gene_annotation_episode.episodic_workflow.episode_support.tools.protein_structure.structure_tables import (
    STRUCTURE_BINDINGS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

CHILD_SLOTS = {'left': 'fact_collection/fact_extraction', 'right': 'fact_collection/fact_extraction'}
SERVICES = ()




def identity(store, ref):
    row = store.get(ref)
    return {'artifact_ref': ref, 'sha256': row['sha256'], 'byte_length': row['size'], 'format': 'text'}


def stage(arguments, ctx):
    """``_stage_retained`` and ``retained_protein_structure_bytes`` on a held artifact."""
    wanted = identity(ctx.store, arguments['ref'])
    directory = _staging(arguments['workspace'], {'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
                                                  'operation_key': ctx.operation_key})
    first = _stage_retained(ctx.store, wanted, directory)
    again = _stage_retained(ctx.store, wanted, directory)
    wrong = {**wanted, 'sha256': hashlib.sha256(b'other').hexdigest()}
    try:
        retained_protein_structure_bytes(ctx.store, wrong)
        refused = None
    except ValueError as error:
        refused = str(error)
    return {'text': Path(first).read_text(), 'same_path': first == again,
            'bytes': retained_protein_structure_bytes(ctx.store, wanted).decode(), 'refused': refused}


def window(arguments, ctx):
    """``source_window`` reads the source's artifact by descriptor, with no path."""
    source = ctx.store.put('source', {**SOURCE, 'artifact_ref': arguments['ref'], 'text_ref': arguments['ref']},
                           origin='caller')['id']
    return source_window(ctx.store, source, offset=2, limit=5, representation='text')


def components(arguments, ctx):
    """``component_chunks`` of an unpacked member, read through the held artifact."""
    member = {'sequence_ref': arguments['ref'], 'quality_ref': None}
    return {'bytes': b''.join(component_chunks(ctx.store, member, 'sequence', offset=1, limit=4)).decode()}


def failure(arguments, ctx):
    try:
        raise ContractError('provider_unreachable')
    except ContractError as error:
        outcome = failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')
    return {'status': outcome['status'], 'code': outcome['feedback']['code'],
            'diagnostic': json.loads(ctx.store.get_artifact(outcome['feedback']['diagnostic_ref']))}


def binding_rows(arguments, ctx):
    """The structure-binding table: a row per source, read back by its source."""
    source = ctx.store.put('source', {**SOURCE, 'artifact_ref': arguments['ref'], 'text_ref': arguments['ref']},
                           origin='caller')['id']
    ctx.store.table(STRUCTURE_BINDINGS).put({'source_ref': source, 'body': json.dumps({'target_ref': None})})
    rows = ctx.store.table(STRUCTURE_BINDINGS).select({'source_ref': source})
    return {'count': len(rows), 'body': json.loads(rows[0]['body'])}



def idle(arguments, ctx):
    """Nothing is left of the plan: this unit does nothing."""
    return {'idle': True}


TOOLS = {'idle': idle, 'stage': stage, 'window': window, 'components': components, 'failure': failure,
         'binding_rows': binding_rows}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    item = summary['plan'][step]
    return ToolCall(item['tool'], item['arguments'])


def action(response, summary, records, ctx):
    """This episode asks the model nothing: its plan is tool calls."""
    return ToolCall('idle', {})
