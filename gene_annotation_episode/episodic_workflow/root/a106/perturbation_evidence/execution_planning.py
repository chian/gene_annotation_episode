"""Original selected-tool recipes and timing views for this scientific invocation."""
from ..execution_planning import memory_for
from ..execution_memory import validate_profile
from ..execution_contracts import obj


def catalog():
    text = {'type': 'string', 'minLength': 1}
    profile = obj({key: text for key in ('resource_id', 'tool', 'implementation', 'parameters', 'hardware')}
                  | {'backend': {'enum': ['local', 'hpc', 'api']}})
    return [{'name': 'process.execution', 'description': 'Read execution instructions for an actual selected '
        'tool/resource pair, current local/Aurora planning context, available HPC commissions and '
        'shared age-weighted timing cases for explicit compatibility profiles. No job, probe or credit.',
        'input_schema': obj({'name': text, 'resources': {'enum': ['local', 'hpc', 'api']},
            'profiles': {'type': 'array', 'maxItems': 8, 'items': profile}})}]


def read(binding, context, arguments):
    # Only a real immutable tool selection can obtain an execution recipe.
    selected = binding.tool_library.resolve_tool_info([
        {key: arguments[key] for key in ('name', 'resources')}], binding._information_catalog(context.scope))
    workflow = binding.services.workflow
    memory = memory_for(workflow)
    rows = []
    for profile in arguments['profiles']:
        profile = validate_profile(profile)
        rows.append({'profile': profile, 'observations': memory.history(profile, limit=64)})
    commissions = []
    if 'hpc' in workflow.episode_bindings.roles:
        hpc = workflow.episode_bindings.for_role('hpc')
        commissions = [{'commission_id': key, 'objective': value['objective'],
            'resource_id': value['resource_id'], 'execution_profile': value.get('execution_profile')}
            for key, value in hpc.commissions.items()]
    return {'tool': selected[0], 'resource_context': workflow.resource_context(context),
        'timing_history': rows, 'known_timing_profiles': memory.profiles(), 'hpc_commissions': commissions,
        'evidence_role': 'operational_planning_only', 'scientific_credit': 0}
