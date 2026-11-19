"""The goal of A101 ``resource_work_submission/api_resource_work_execution`` (old role ``launch_api``).

Carried over from this episode's own ``goal.py`` at ``97308b94c``: the responsibility table (all five resource
roles, as the old file held them; this episode uses its own entry), the common tail, and the
contract-information ``discovery`` paragraph, which the old ``episode.py`` only ever added for the role
``launch`` and therefore never for this episode.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import RESOURCE_ROLES

ROLE = 'launch_api'
RESOURCE_KIND = RESOURCE_ROLES[ROLE]

RESPONSIBILITIES = {
    'launch': 'Choose which actual execution approach is productive within the assigned job and constraints; commission a resource child when useful.',
    'launch_api': 'Investigate execution through the selected actual API or service, including real availability and authentication.',
    'launch_local': 'Investigate preparation, execution and receiving interfaces on the selected local resource.',
    'launch_hpc': 'Investigate the selected actual environment, queue, staging and execution interfaces.',
    'results': 'Acquire the requested data through the supplied receiving interface; the scientific parent interprets it.',
}
RESPONSIBILITY = RESPONSIBILITIES[ROLE]
COMMON_TAIL = (' Revise later choices from actual outcomes. Ordinary operations are tools; iteration belongs to this'
               ' shared Episode. Preserve the parent job, input versions, CPU, search and constraints. Capabilities'
               ' and duration estimates inform your decisions, without selecting an approach or imposing an order.'
               ' Unknown/authentication-required resources remain explicit. Return the original parent-defined'
               ' typed form. Only the configured local controller governs continuation.')
DISCOVERY = (" Within the pending decision, request_context with view=composition_information, operation=episode.return_contract"
             " and arguments role/source describes the permitted child's exact frozen fact contract. Select a top-level"
             " form field with only $ref set to episode-fact:<source> to have the host expand and fill that type."
             " Choose the facts needed for the job. If a usable handoff is still uncertain, retaining the original"
             " job_ref and receiving state allows later work to repair that job without submitting a replacement.")

# The binding's grain description (BINDING_CONTRACT ``goal``/``unit``/``result``).
GOAL = RESPONSIBILITY
UNIT = 'One tool, typed reasoning commitment or wait on the one selected API resource'
RESULT = 'The execution handoff facts of the selected API resource, and the parent-defined typed form when one is commissioned'


def contract_information_profile():
    """The old ``contract_information_profile(context)``: a profile only for the role ``launch``; never this role."""
    return None


def instructions():
    """The old ``OperationalGoal.instructions(context)``: this role's responsibility, the common tail, no discovery."""
    discovery = DISCOVERY if contract_information_profile() is not None else ''
    return RESPONSIBILITY + COMMON_TAIL + discovery
