"""The A102 head's continuation (carried from ``yield_estimator.py`` and the yield checks of ``episode.py`` at
``97308b94c``).

The old head declared, per commissioned task ``A102:<task>``, one of the three estimators in its configured
``yield_bindings``: ``{'kind', 'cutoff', 'parameters' ({'uncertainty_alpha'}), 'credit_definition'}``. The
declaration had to exist, its ``credit_definition`` had to equal the projector's record and its ``kind`` the
projector's ``yield_method``; ``accumulation`` was ``YieldController``, ``bounded_quality`` was
``BoundedYieldController`` with ``projector.native_score_maximum`` as its maximum. They are now the accumulation
and the bounded-quality controllers (README 7b); the old ``completion`` kind had no target and no A102 projector's
``yield_method`` is ``completion``, so a ``completion`` declaration fails at the declaration check, as a
declaration for another kind would. The old cutoff is the controller's ``cost``.

The head's ``settings`` (its entry of the run's ``continuation`` collaborator) hold ``yield_bindings``: the
declarations by task key. Everything else is read from the parent input: the task key, the projector's record,
its estimator kind and its declared maximum (``messages/read_from_parent.py`` made them from the assignment).
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration, open_yield_controller)

EPOCH = 'structural_homology_evidence'
KINDS = ('accumulation', 'bounded_quality', 'completion')


def check_declarations(declarations):
    """The old ``__init__`` check of each declaration: exactly kind, cutoff, parameters (``uncertainty_alpha``
    only) and credit_definition."""
    for task, declaration in declarations.items():
        if (not isinstance(task, str) or ':' not in task or not isinstance(declaration, dict)
                or set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
                or declaration['kind'] not in KINDS or not isinstance(declaration['parameters'], dict)
                or set(declaration['parameters']) != {'uncertainty_alpha'}
                or not isinstance(declaration['credit_definition'], dict) or not declaration['credit_definition']):
            raise ValueError('scientific_yield_task_binding_invalid:' + str(task))


def yield_controller(initial_credit, settings, parent_input):
    declarations = settings['yield_bindings']
    check_declarations(declarations)
    declaration = checked_yield_declaration(
        declarations, parent_input['task_key'], credit_definition=parent_input['credit_definition'],
        yield_method=parent_input['yield_method'], code_prefix='scientific')
    maximum = parent_input['native_score_maximum'] if declaration['kind'] == 'bounded_quality' else None
    return open_yield_controller(declaration['kind'], epoch=EPOCH, initial_credit=initial_credit,
                                 cutoff=declaration['cutoff'], parameters=declaration['parameters'],
                                 maximum_credit=maximum)
