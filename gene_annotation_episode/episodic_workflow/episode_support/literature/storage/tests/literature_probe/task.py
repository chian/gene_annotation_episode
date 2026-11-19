"""The task: run the plan of the commission, one tool per step; after the plan the episode offers ``idle``.

Every tool builds a repository of the literature storage library over ``ctx.store``, the custody-scoped store of
the unit, and returns what the library returned."""
from episode_runtime import Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    LiteratureA108GradingRepository, REQUESTED)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_repositories import (
    LiteratureContext)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence import (
    literature_sheet_updates as updates)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence.literature_aggregation_storage import (
    LiteratureA108AggregationRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence.literature_rate_storage import (
    LiteratureRateRepository)

CHILD_SLOTS = {}
SERVICES = ()


def literature_context(arguments):
    return LiteratureContext('literature', arguments['scope'], {REQUESTED: arguments['requested']})


def grade(arguments, ctx):
    """Save one contextual grading sheet; what the operation returned."""
    repository = LiteratureA108GradingRepository(ctx.store)
    outcome = repository.populate(literature_context(arguments), arguments['population'], ctx.operation_key)
    return {'outcome': outcome, 'operation_key': ctx.operation_key}


def look(arguments, ctx):
    """What the Episode holds of the sheets after the saves: ownership, rows, saved sheets and current cells."""
    store = ctx.store
    context = literature_context(arguments)
    grading = LiteratureA108GradingRepository(store)
    main = LiteratureA108AggregationRepository(store)
    owned = grading.owned_sheet_refs()
    return {'grading_sheets': owned, 'aggregation_sheets': main.owned_sheet_refs(),
            'grading_cells': [row['cell']['component'] for row in store.table(grading.cells_table).select()],
            'grading_cell_rows': [row['id'] for row in store.table(grading.cells_table).select()],
            'aggregation_cells': [row['cell']['component'] for row in store.table(main.cells_table).select()],
            'dependencies': [(row['sheet_ref'], row['family'], row['current_status'])
                             for row in updates._rows(store)],
            'current': [{key: cell[key] for key in ('sheet_ref', 'support_count', 'conflict_count', 'observation_sets')}
                        for cell in main.current_annotation_cells(context)],
            'saved': {ref: grading.read(ref)['sheet']['cells'] for ref in owned},
            'owns': [grading.owns(ref) for ref in owned],
            'main_saved': {ref: main.read(ref)['sheet']['cells']['overall'] for ref in main.owned_sheet_refs()}}


def foreign(arguments, ctx):
    """Reading a sheet the Episode did not produce: its ownership and the cells it holds."""
    store = ctx.store
    context = literature_context(arguments)
    grading = LiteratureA108GradingRepository(store)
    return {'owns': grading.owns(arguments['sheet_ref']),
            'facts': grading.fact_cells(context, [arguments['sheet_ref']], components=arguments['components']),
            'received': grading.received_cells(context)}


def rate_populate(arguments, ctx):
    """Save one rate sheet from a retained table."""
    repository = LiteratureRateRepository(ctx.store)
    outcome = repository.populate(literature_context(arguments), arguments['population'], ctx.operation_key)
    return {'outcome': outcome}


def rate_look(arguments, ctx):
    """The rate sheets and cells the Episode holds, read back."""
    store = ctx.store
    context = literature_context(arguments)
    repository = LiteratureRateRepository(store)
    owned = repository.owned_sheet_refs()
    return {'owned': owned, 'saved': [repository.read(ref)['input_source_ref'] for ref in owned],
            'cells': repository.project_cells(owned, components=arguments['components']),
            'facts': repository.fact_cells(context, owned, components=arguments['components']),
            'cell_rows': [row['id'] for row in store.table(repository.cells_table).select()],
            'received': repository.received_cells(context),
            'source_view': repository.source_projection().owned_sheet_refs(),
            'registered': updates.current_sheet_refs(store, context)}


def rate_foreign(arguments, ctx):
    """A sheet this Episode did not produce: not owned; its cells are the cell rows it holds."""
    context = literature_context(arguments)
    repository = LiteratureRateRepository(ctx.store)
    return {'owns': repository.owns(arguments['sheet_ref']),
            'facts': repository.fact_cells(context, [arguments['sheet_ref']], components=arguments['components']),
            'received': repository.received_cells(context)}


def idle(arguments, ctx):
    """Nothing is left of the plan: this unit does nothing."""
    return {'idle': True}


TOOLS = {'idle': idle, 'grade': grade, 'look': look, 'foreign': foreign, 'rate_populate': rate_populate,
         'rate_look': rate_look, 'rate_foreign': rate_foreign}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    item = summary['plan'][step]
    return ToolCall(item['tool'], item['arguments'])


def action(response, summary, records, ctx):
    raise Rejected({'status': 'invalid', 'category': 'no_model_decision', 'detail': 'this task decides by plan'})
