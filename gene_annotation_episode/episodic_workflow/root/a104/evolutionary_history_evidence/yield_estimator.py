"""The continuation: the credit task's own declared yield, one of the three controllers.

Carried from the old ``yield_estimator.py`` (``continuation_task``, ``yield_controller``) and ``configuration.py``
(the check of the declared bindings, ``scientific_yield_task_binding_invalid``). The task key is
``A104:<a104_task name>`` or ``A104:<projector kind>``; the declaration configured for that key fixes ``kind``, the
cost (the old ``cutoff``), ``parameters`` (``uncertainty_alpha``) and ``credit_definition``; the definition must equal
the projector's record and the projector's ``yield_method`` must equal the kind. README 7b: ``accumulation`` is
``AccumulationYieldController``; ``bounded_quality`` is ``BoundedQualityYieldController`` with the projector's
``native_score_maximum``; ``completion`` is ``CompletionYieldController`` with the finite target of the credit
definition (the projector's declared ``maximum_credit``, which the parent input selects through ``a104_task``).

Settings (``settings``, the episode's entry of the ``continuation`` collaborator): ``yield_bindings`` (the old
``yield_bindings``: ``{task key: {kind, cutoff, parameters, credit_definition}}``) and ``process_library_directory``
(the frozen process library, to tell an evidence-axis instruction entry from an older entry). An older entry has no
credit projector, so the old ``continuation_task`` raised ``scientific_task_credit_not_declared``: it does here."""
from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration, open_yield_controller)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.evolutionary_history_evidence.evidence_axis_instructions import (
    VERSION as INSTRUCTION_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.evolutionary_history_evidence.process_options import (
    EvolutionaryHistoryEvidenceLibrary)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.construction_records import (
    selection_fields)

from .credit import credit_projector

AXIS = 'A104'
KINDS = ('accumulation', 'bounded_quality', 'completion')
DECLARATION_KEYS = {'kind', 'cutoff', 'parameters', 'credit_definition'}


def validate_yield_bindings(bindings):
    """The old ``ScientificConfiguration.__init__`` check of the declared bindings, with the old throwaway controller
    of each declaration opened by ``open_yield_controller`` at ``epoch='configuration'``."""
    if not isinstance(bindings, dict):
        raise ContractError('scientific_yield_bindings_invalid')
    for task, declaration in bindings.items():
        if (not isinstance(task, str) or ':' not in task or not isinstance(declaration, dict)
                or set(declaration) != DECLARATION_KEYS or declaration['kind'] not in KINDS
                or not isinstance(declaration['parameters'], dict)
                or set(declaration['parameters']) != {'uncertainty_alpha'}
                or not isinstance(declaration['credit_definition'], dict) or not declaration['credit_definition']):
            raise ContractError('scientific_yield_task_binding_invalid:' + str(task))
        try:
            kind = declaration['kind']
            open_yield_controller(kind, epoch='configuration', initial_credit=0, cutoff=declaration['cutoff'],
                                  parameters=declaration['parameters'],
                                  **({'maximum_credit': 1.0} if kind == 'bounded_quality' else {}),
                                  **({'target': 1.0} if kind == 'completion' else {}))
        except (TypeError, ValueError) as error:
            raise ContractError('scientific_yield_task_binding_invalid:' + task) from error


def continuation_task(parent_input, projector):
    assigned = parent_input['a104_task']
    if assigned is not None:
        if not isinstance(assigned.get('name'), str) or not assigned['name']:
            raise ContractError('scientific_continuation_original_task_required')
        return AXIS + ':' + assigned['name']
    return AXIS + ':' + projector.as_record()['kind']


def yield_controller(initial_credit, settings, parent_input):
    bindings = settings['yield_bindings']
    validate_yield_bindings(bindings)
    if not parent_input['proposed_annotation_ref']:
        raise ContractError('scientific_task_proposed_annotation_required')
    selection = parent_input['selection']
    library = EvolutionaryHistoryEvidenceLibrary(settings['process_library_directory'])
    axis = library.resolve(selection[selection_fields(selection)[0]])
    if axis.get('entry_version') != INSTRUCTION_VERSION:
        raise ContractError('scientific_task_credit_not_declared')
    projector = credit_projector(parent_input)
    task = continuation_task(parent_input, projector)
    declaration = checked_yield_declaration(bindings, task, credit_definition=projector.as_record(),
                                            yield_method=projector.yield_method, code_prefix='scientific')
    kind = declaration['kind']
    extra = {}
    if kind == 'bounded_quality':
        extra['maximum_credit'] = projector.native_score_maximum
    elif kind == 'completion':
        extra['target'] = projector.as_record()['maximum_credit']
    return open_yield_controller(kind, epoch='evolutionary_history_evidence', initial_credit=initial_credit,
                                 cutoff=declaration['cutoff'], parameters=declaration['parameters'], **extra)
