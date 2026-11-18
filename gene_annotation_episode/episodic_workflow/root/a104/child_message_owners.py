"""A104 cached nominal parent/child identity; no provider or registry calls."""
import sys
from types import GetSetDescriptorType, ModuleType

def _static(cls, name):
    if type(cls) is not type:
        return None
    for base in type.__getattribute__(cls, '__mro__'):
        namespace = type.__getattribute__(base, '__dict__')
        if name in namespace:
            return namespace[name]
    return None

def _state(value):
    cls = type(value)
    if _static(cls, '__getattribute__') is not object.__getattribute__ or _static(cls, '__getattr__') is not None or type(_static(cls, '__dict__')) is not GetSetDescriptorType:
        return None
    state = object.__getattribute__(value, '__dict__')
    return state if type(state) is dict and all((type(key) is str for key in state)) else None

def _current_class(module, name):
    provider = sys.modules.get(__package__ + '.' + module)
    if type(provider) is not ModuleType:
        return None
    result = vars(provider).get(name)
    return result if type(result) is type else None

def _identity(binding):
    state = _state(binding)
    names = ('binding_path', 'commissioning_parent', 'roles', 'entry_roles')
    if state is None or any((name in state for name in names)):
        return None
    path, parent, roles, entries = (_static(type(binding), name) for name in names)
    if type(path) is not str or type(parent) is not str or type(roles) is not tuple or (type(entries) is not tuple) or (not all((type(role) is str for role in roles + entries))):
        return None
    return (path, parent, roles, entries)

def _registry(workflow):
    state = _state(workflow)
    if state is None:
        return None
    registry = state.get('episode_bindings')
    cls = _current_class('episode_bindings', 'EpisodeBindingRegistry')
    if cls is None or type(registry) is not cls:
        return None
    state = _state(registry)
    if state is None:
        return None
    by_role, by_path = (state.get('_by_role'), state.get('_by_path'))
    if type(by_role) is not dict or type(by_path) is not dict or (not all((type(key) is str for key in by_role))) or (not all((type(key) is str for key in by_path))):
        return None
    return (by_role, by_path)

def _nominal_episode_child(workflow, role, home, class_name, parent):
    cached = _registry(workflow)
    if cached is None:
        return False
    by_role, by_path = cached
    candidates = by_role.get(role, ())
    if type(candidates) not in (tuple, list):
        return False
    selected = by_path.get(home)
    nominal = _current_class(home.replace('/', '.') + '.episode', class_name)
    if nominal is None or type(selected) is not nominal:
        return False
    matches = []
    for candidate in candidates:
        identity = _identity(candidate)
        if identity is None:
            return False
        path, commissioner, _, entries = identity
        if by_path.get(path) is not candidate:
            return False
        if parent is None and commissioner in ('legacy_annotation', 'annotation') and (role in entries) or (parent is not None and commissioner == parent):
            matches.append(candidate)
    if parent == 'evolutionary_history_evidence' and role == 'evolutionary_history_evidence' and (not matches):
        state = _state(selected)
        if state is None:
            return False
        children = state.get('_child_roles')
        if type(children) is not tuple or not all((type(item) is str for item in children)):
            return False
        identity = _identity(selected)
        if identity is None or identity[0] != parent or role not in identity[2] or (role not in children):
            return False
        matches.append(selected)
    return len(matches) == 1 and matches[0] is selected

def _nominal_job_child(workflow, role, home):
    state = _state(workflow)
    if state is None:
        return False
    jobs = state.get('job_episodes')
    family_type = _current_class('homology_binding_family', 'HomologyBindingFamily')
    nominal = _current_class(home + '.episode', 'HomologyEpisode')
    if nominal is None:
        return False
    if family_type is not None and type(jobs) is family_type:
        state = _state(jobs)
        if state is None:
            return False
        bindings = state.get('_private_bindings')
        if type(bindings) is not dict or not all((type(key) is str for key in bindings)):
            return False
        chosen = bindings.get(role)
    else:
        chosen = jobs
    if type(chosen) is not nominal:
        return False
    identity = _identity(chosen)
    return identity is not None and identity[0] == home and (identity[1] == 'legacy_annotation') and (role in identity[2])

def _scientific_parent(workflow, source):
    runtime = sys.modules.get(__package__ + '.runtime')
    if type(runtime) is not ModuleType or type(workflow) is not vars(runtime).get('_annotation_original_workflow'):
        return False
    nominal = _current_class('evolutionary_history_evidence.task', 'ScientificTask')
    if nominal is None or type(source) is not nominal:
        return False
    state = _state(source)
    if state is None or state.get('workflow') is not workflow:
        return False
    path = state.get('path')
    if type(path) is not tuple or not path or (not all((type(part) is tuple and len(part) == 2 and all((type(item) is str and item for item in part)) for part in path))):
        return False
    roles = tuple((part[0] for part in path))
    cached = _registry(workflow)
    if cached is None:
        return False
    by_role, by_path = cached
    if roles[0] == 'annotation':
        if 'annotation' in by_role:
            return False
        roles = roles[1:]
    if not roles or any((role != 'evolutionary_history_evidence' for role in roles)):
        return False
    scientific = by_path.get('evolutionary_history_evidence')
    nominal = _current_class('evolutionary_history_evidence.episode', 'EvolutionaryHistoryEvidenceEpisode')
    if nominal is None or type(scientific) is not nominal:
        return False
    candidates = by_role.get('evolutionary_history_evidence')
    if type(candidates) not in (tuple, list) or len(candidates) != 1 or candidates[0] is not scientific:
        return False
    state = _state(scientific)
    if state is None:
        return False
    if len(roles) > 1:
        children = state.get('_child_roles')
        if type(children) is not tuple or not all((type(role) is str for role in children)) or 'evolutionary_history_evidence' not in children:
            return False
    return _identity(scientific) == ('evolutionary_history_evidence', 'legacy_annotation', ('evolutionary_history_evidence',), ('evolutionary_history_evidence',))

def parent_exchange(workflow, source, selection, role):
    if type(selection) is not dict or not all((type(key) is str for key in selection)) or type(role) is not str:
        return None
    kind = selection.get('kind')
    if type(kind) is not str:
        return None
    from .episode import is_annotation_parent
    if is_annotation_parent(workflow, source):
        if kind == 'child' and role == 'improvement':
            from .annotation_improvement.episode import unbound_improvement_domain
            if not unbound_improvement_domain(workflow):
                return None
            from .to_child_annotation_improvement import prepare_parent_request, assemble_parent_request
            from .from_child_annotation_improvement import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'episode_child' and role == 'launch':
            if not _nominal_episode_child(workflow, role, 'execution_job_submission', 'ExecutionEpisode', None):
                return None
            from .to_child_execution_job_submission import prepare_parent_request, assemble_parent_request
            from .from_child_execution_job_submission import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'episode_child' and role == 'monitor':
            if not _nominal_episode_child(workflow, role, 'execution_progress_assessment', 'MonitorEpisode', None):
                return None
            from .to_child_execution_progress_assessment import prepare_parent_request, assemble_parent_request
            from .from_child_execution_progress_assessment import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'episode_child' and role == 'results':
            if not _nominal_episode_child(workflow, role, 'execution_result_acquisition', 'ExecutionEpisode', None):
                return None
            from .to_child_execution_result_acquisition import prepare_parent_request, assemble_parent_request
            from .from_child_execution_result_acquisition import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'episode_child' and role == 'literature':
            if not _nominal_episode_child(workflow, role, 'published_evidence_assessment', 'LiteratureEpisode', None):
                return None
            from .to_child_published_evidence_assessment import prepare_parent_request, assemble_parent_request
            from .from_child_published_evidence_assessment import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'episode_child' and role == 'hpc':
            if not _nominal_episode_child(workflow, role, 'hpc_work_planning', 'HPCEpisode', None):
                return None
            from .to_child_hpc_work_planning import prepare_parent_request, assemble_parent_request
            from .from_child_hpc_work_planning import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'episode_child' and role == 'evolutionary_history_evidence':
            if not _nominal_episode_child(workflow, role, 'evolutionary_history_evidence', 'EvolutionaryHistoryEvidenceEpisode', None):
                return None
            from .to_child_evolutionary_history_evidence import prepare_parent_request, assemble_parent_request
            from .from_child_evolutionary_history_evidence import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'job_child' and role == 'job_launch':
            if not _nominal_job_child(workflow, role, 'homology_job_submission'):
                return None
            from .to_child_homology_job_submission import prepare_parent_request, assemble_parent_request
            from .from_child_homology_job_submission import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'job_child' and role == 'job_monitor':
            if not _nominal_job_child(workflow, role, 'homology_job_monitoring'):
                return None
            from .to_child_homology_job_monitoring import prepare_parent_request, assemble_parent_request
            from .from_child_homology_job_monitoring import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'job_child' and role == 'job_results':
            if not _nominal_job_child(workflow, role, 'homology_result_acquisition'):
                return None
            from .to_child_homology_result_acquisition import prepare_parent_request, assemble_parent_request
            from .from_child_homology_result_acquisition import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        return None
    from .annotation_improvement.episode import is_improvement_parent
    if is_improvement_parent(workflow, source):
        if kind == 'child' and role == 'improvement':
            from .annotation_improvement.to_child_annotation_improvement import prepare_parent_request, assemble_parent_request
            from .annotation_improvement.from_child_annotation_improvement import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'job_child' and role == 'job_launch':
            if not _nominal_job_child(workflow, role, 'homology_job_submission'):
                return None
            from .annotation_improvement.to_child_homology_job_submission import prepare_parent_request, assemble_parent_request
            from .annotation_improvement.from_child_homology_job_submission import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'job_child' and role == 'job_monitor':
            if not _nominal_job_child(workflow, role, 'homology_job_monitoring'):
                return None
            from .annotation_improvement.to_child_homology_job_monitoring import prepare_parent_request, assemble_parent_request
            from .annotation_improvement.from_child_homology_job_monitoring import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        if kind == 'job_child' and role == 'job_results':
            if not _nominal_job_child(workflow, role, 'homology_result_acquisition'):
                return None
            from .annotation_improvement.to_child_homology_result_acquisition import prepare_parent_request, assemble_parent_request
            from .annotation_improvement.from_child_homology_result_acquisition import admit_parent_return, receive_parent_child_failure
            return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, assemble_parent_request)
        return None
    if kind != 'episode_child' or not _scientific_parent(workflow, source):
        return None
    if role == 'evolutionary_history_evidence':
        if not _nominal_episode_child(workflow, role, 'evolutionary_history_evidence', 'EvolutionaryHistoryEvidenceEpisode', 'evolutionary_history_evidence'):
            return None
        from .evolutionary_history_evidence.to_child_evolutionary_history_evidence import prepare_parent_request
        from .evolutionary_history_evidence.from_child_evolutionary_history_evidence import admit_parent_return, receive_parent_child_failure
        return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, None)
    if role == 'hpc':
        if not _nominal_episode_child(workflow, role, 'evolutionary_history_evidence/hpc_work_planning', 'HPCEpisode', 'evolutionary_history_evidence'):
            return None
        from .evolutionary_history_evidence.to_child_hpc_work_planning import prepare_parent_request
        from .evolutionary_history_evidence.from_child_hpc_work_planning import admit_parent_return, receive_parent_child_failure
        return (prepare_parent_request, admit_parent_return, receive_parent_child_failure, None)
    return None
