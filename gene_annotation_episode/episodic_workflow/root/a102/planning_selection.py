"""Declared A102 Resource portfolios for actual registered caller homes.

This is a planning-information route only. It creates no received-input authority,
invocation, resource reservation, job, grade or credit. Generic/HPC execution homes
are nonparticipants and retain their original global lookup.
"""
from importlib import import_module

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a102'
# (literal private home, literal commissioning parent, role, class, portfolio)
CALLERS = {
    'scientific_process': ('legacy_annotation', 'scientific_process', 'ScientificProcessEpisode', 'scientific_process/resource_work_submission'),
    'execution_progress_assessment': ('legacy_annotation', 'monitor', 'MonitorEpisode', 'resource_work_submission'),
    'scientific_process/execution_progress_assessment': ('scientific_process', 'monitor', 'MonitorEpisode', 'scientific_process/resource_work_submission'),
    'resource_work_submission': ('legacy_annotation', 'launch', 'ResourceEpisode', 'resource_work_submission'),
    'resource_work_submission/api_resource_work_execution': ('resource_work_submission', 'launch_api', 'ResourceEpisode', 'resource_work_submission'),
    'resource_work_submission/local_resource_work_execution': ('resource_work_submission', 'launch_local', 'ResourceEpisode', 'resource_work_submission'),
    'resource_work_submission/hpc_resource_work_execution': ('resource_work_submission', 'launch_hpc', 'ResourceEpisode', 'resource_work_submission'),
    'resource_result_acquisition': ('legacy_annotation', 'results', 'ResourceEpisode', 'resource_work_submission'),
    'scientific_process/resource_work_submission': ('scientific_process', 'launch', 'ResourceEpisode', 'scientific_process/resource_work_submission'),
    'scientific_process/resource_work_submission/api_resource_work_execution': ('scientific_process/resource_work_submission', 'launch_api', 'ResourceEpisode', 'scientific_process/resource_work_submission'),
    'scientific_process/resource_work_submission/local_resource_work_execution': ('scientific_process/resource_work_submission', 'launch_local', 'ResourceEpisode', 'scientific_process/resource_work_submission'),
    'scientific_process/resource_work_submission/hpc_resource_work_execution': ('scientific_process/resource_work_submission', 'launch_hpc', 'ResourceEpisode', 'scientific_process/resource_work_submission'),
    'scientific_process/resource_result_acquisition': ('scientific_process', 'results', 'ResourceEpisode', 'scientific_process/resource_work_submission'),
    'published_evidence_assessment': ('legacy_annotation', 'literature', 'LiteratureEpisode', 'resource_work_submission'),
    'published_evidence_assessment/evidence_search_strategy_improvement': ('published_evidence_assessment', 'literature_strategy', 'LiteratureEpisode', 'resource_work_submission'),
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment': ('published_evidence_assessment/evidence_search_strategy_improvement', 'literature_search', 'LiteratureEpisode', 'resource_work_submission'),
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination': ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', 'literature_page', 'LiteratureEpisode', 'resource_work_submission'),
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction': ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_table', 'LiteratureEpisode', 'resource_work_submission'),
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement': ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_ordered', 'LiteratureEpisode', 'resource_work_submission'),
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction': ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_targeted', 'LiteratureEpisode', 'resource_work_submission'),
    'scientific_process/published_evidence_assessment': ('scientific_process', 'literature', 'LiteratureEpisode', 'scientific_process/resource_work_submission'),
    'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement': ('scientific_process/published_evidence_assessment', 'literature_strategy', 'LiteratureEpisode', 'scientific_process/resource_work_submission'),
    'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment': ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement', 'literature_search', 'LiteratureEpisode', 'scientific_process/resource_work_submission'),
    'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination': ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', 'literature_page', 'LiteratureEpisode', 'scientific_process/resource_work_submission'),
    'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction': ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_table', 'LiteratureEpisode', 'scientific_process/resource_work_submission'),
    'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement': ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_ordered', 'LiteratureEpisode', 'scientific_process/resource_work_submission'),
    'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction': ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_targeted', 'LiteratureEpisode', 'scientific_process/resource_work_submission'),
}
RESOURCE_HOMES = tuple(home for home,row in CALLERS.items() if row[2] == 'ResourceEpisode')


def _original(registry):
    return registry.for_role('launch') if 'launch' in registry.roles else None


def _authentic(registry, binding, home):
    parent, role, classname, _ = CALLERS[home]
    return (registry.for_binding_path(home) is binding
        and type(binding) is getattr(import_module(PACKAGE+'.'+home.replace('/', '.')+'.episode'), classname)
        and binding.binding_path == home and binding.commissioning_parent == parent
        and binding.roles == (role,))


def _require(registry, binding, home):
    if not _authentic(registry, binding, home):
        raise ValueError('a102_resource_planning_private_identity_mismatch:'+home)
    return binding


def _possible_participant(path):
    # Inspect the complete finite role graph before a standalone role lookup.
    # This boolean never selects a portfolio or authorizes any saved edge.
    if not isinstance(path, (tuple, list)) or not path:
        return False
    possible = set()
    resource_frame = False
    for index, part in enumerate(path):
        if not isinstance(part, (tuple, list)) or not part or not isinstance(part[0], str):
            return resource_frame
        role = part[0]
        if index == 0:
            possible = ({'legacy_annotation'} if role == 'annotation' else
                        {home for home, row in CALLERS.items() if row[1] == role})
        else:
            following = set()
            for home in possible:
                direct = {candidate for candidate, row in CALLERS.items()
                          if row[0] == home and row[1] == role}
                if not direct and home in CALLERS and CALLERS[home][1] == role:
                    direct = {home}
                following.update(direct)
            if not following:
                return resource_frame or bool(possible) and role in {'launch_api','launch_local','launch_hpc'}
            possible = following
        if not possible:
            return False
        resource_frame = resource_frame or bool(possible.intersection(RESOURCE_HOMES))
    return bool(possible)


def _declared_portfolio(registry, path):
    # Classify only the finite declared caller-role graph before validating its
    # saved keys. Unknown/nonparticipating malformed paths retain the original
    # global lookup timing. No role selects the eventual Launch counterpart.
    if not isinstance(path, (tuple, list)) or not path:
        return None
    home = 'legacy_annotation'
    resource_frame = False
    for index, part in enumerate(path):
        if not isinstance(part, (tuple, list)) or not part or not isinstance(part[0], str):
            return CALLERS[home][3] if resource_frame else None
        role = part[0]
        if index == 0 and role == 'annotation' and role not in registry.roles:
            continue
        if index == 0:
            if role not in {row[1] for row in CALLERS.values()}:
                return None
            # This is the registry's pre-existing standalone SOURCE identity,
            # not a uniqueness-based choice of another parent's counterpart.
            source = registry.for_role(role)
            home = getattr(source, 'binding_path', None)
            if home not in CALLERS:
                return None
        else:
            matches = [candidate for candidate,row in CALLERS.items()
                       if row[0] == home and row[1] == role]
            if not matches and home in CALLERS and CALLERS[home][1] == role:
                matches = [home]
            if len(matches) != 1:
                if role in {'launch_api','launch_local','launch_hpc'}:
                    return 'resource_work_submission' if home == 'legacy_annotation' else CALLERS[home][3]
                return CALLERS[home][3] if resource_frame else None
            home = matches[0]
        resource_frame = resource_frame or home in RESOURCE_HOMES
    return 'resource_work_submission' if home == 'legacy_annotation' else CALLERS[home][3]


def planning_binding(workflow, source):
    registry = workflow.episode_bindings
    resources = []
    # Occupied literal Resource homes with foreign implementations are errors,
    # not absence of opt-in and not permission for a global same-role substitute.
    for home in RESOURCE_HOMES:
        if home in registry._by_path:
            resources.append(_require(registry, registry._by_path[home], home))
    if not resources:
        return _original(registry)
    if not _possible_participant(getattr(source, 'path', None)):
        return _original(registry)
    portfolio = _declared_portfolio(registry, source.path)
    if portfolio is None:
        return _original(registry)
    if not any(CALLERS[home][3] == portfolio and home in registry._by_path
               for home in RESOURCE_HOMES):
        # This caller's actual factory branch has no Resource portfolio.
        # Preserve its historical generic behavior as a separate limitation.
        return _original(registry)
    path = tuple(tuple(part) for part in source.path)
    if not path or any(len(part)!=2 or any(not isinstance(item,str) or not item for item in part) for part in path):
        raise ValueError('episode_binding_runtime_path_required')
    parent = None
    home = 'legacy_annotation'
    selected = None
    science_frames = []
    resource_frame = False
    for index, (role, _) in enumerate(path):
        prefix = path[:index+1]
        if index == 0 and role == 'annotation' and role not in registry.roles:
            continue
        if index == 0:
            if role not in {row[1] for row in CALLERS.values()}:
                return _original(registry)
            # Preserve the registry's existing standalone-source resolution.
            # Its role lookup identifies that source only, never a counterpart.
            actual = registry.for_role(role)
            actual_home = getattr(actual, 'binding_path', None)
            if actual_home not in CALLERS:
                return _original(registry)
            parent = selected = _require(registry, actual, actual_home)
            home = actual_home
            resource_frame = home in RESOURCE_HOMES
            if home == 'scientific_process':
                science_frames.append(prefix)
            continue
        matches = [candidate for candidate,row in CALLERS.items() if row[0]==home and row[1]==role]
        if home in CALLERS and CALLERS[home][1] == role and role in parent.child_roles(role):
            # The actual registry chooses a declared direct child before a
            # recursive frame. Do not override that ordering with this table.
            if not matches:
                matches = [home]
        if not matches:
            registry.for_path(prefix)
            raise ValueError('a102_resource_planning_context_not_declared')
        if len(matches) != 1:
            raise ValueError('a102_resource_planning_declaration_conflict')
        expected = matches[0]
        if parent is None and role not in workflow.declared_child_roles('annotation', path=path[:1]):
            raise ValueError('a102_resource_planning_child_not_declared:'+expected)
        actual = registry._child_binding(parent, role)
        actual_home = getattr(actual, 'binding_path', None)
        if actual_home != expected:
            raise ValueError('a102_resource_planning_private_edge_mismatch:'+expected)
        _require(registry, actual, expected)
        if parent is not None and role not in parent.child_roles(CALLERS[home][1]):
            raise ValueError('a102_resource_planning_child_not_declared:'+expected)
        parent, home, selected = actual, expected, actual
        resource_frame = resource_frame or home in RESOURCE_HOMES
        if home == 'scientific_process':
            science_frames.append(prefix)
    if selected is not None and registry.for_path(path) is not selected:
        raise ValueError('a102_resource_planning_saved_owner_mismatch')
    assert portfolio == ('resource_work_submission' if selected is None else CALLERS[home][3])
    # A standalone actual Resource Launch is its own owner; no invented parent
    # path is needed. A standalone native child/Results/source has no such grant.
    if home == portfolio:
        return _require(registry, selected, portfolio)
    if portfolio == 'scientific_process/resource_work_submission':
        if not science_frames:
            raise ValueError('a102_resource_planning_scientific_parent_required')
        parent_path = science_frames[-1]
        owner = _require(registry, registry.for_path(parent_path), 'scientific_process')
        declared = owner.child_roles('scientific_process')
    else:
        if path[0][0] != 'annotation' or 'annotation' in registry.roles:
            raise ValueError('a102_resource_planning_annotation_parent_required')
        parent_path = path[:1]
        declared = workflow.declared_child_roles('annotation', path=parent_path)
    if 'launch' not in declared:
        raise ValueError('a102_resource_planning_launch_not_declared')
    owner = registry.for_child(parent_path, 'launch')
    return _require(registry, owner, portfolio)
