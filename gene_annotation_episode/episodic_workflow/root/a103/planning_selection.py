"""Explicit Resource-family planning dispatch; all other reads stay original.

Registered role uniqueness never selects a private Resource counterpart. This
finite type graph contains only actual Resource callers, not generic HPC homes.
It grants no invocation, received-result, capacity or scientific authority.
"""
from importlib import import_module
PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a103'
_SOURCE = 'published_evidence_assessment'
_STRATEGY = _SOURCE + '/evidence_search_strategy_improvement'
_SEARCH = _STRATEGY + '/source_relevance_assessment'
_PAGE = _SEARCH + '/source_evidence_examination'
SOURCE_CALLERS = ((_SOURCE, '', 'literature'),
    (_STRATEGY, _SOURCE, 'literature_strategy'),
    (_SEARCH, _STRATEGY, 'literature_search'),
    (_PAGE, _SEARCH, 'literature_page'),
    (_PAGE+'/table_evidence_extraction', _PAGE, 'literature_table'),
    (_PAGE+'/source_coverage_improvement', _PAGE, 'literature_ordered'),
    (_PAGE+'/passage_evidence_extraction', _PAGE, 'literature_targeted'))
RESOURCE_CALLERS = (('resource_work_submission', '', 'launch'),
    ('resource_work_submission/api_resource_work_execution', 'resource_work_submission', 'launch_api'),
    ('resource_work_submission/local_resource_work_execution', 'resource_work_submission', 'launch_local'),
    ('resource_work_submission/hpc_resource_work_execution', 'resource_work_submission', 'launch_hpc'),
    ('resource_result_acquisition', '', 'results'))
CALLERS = {'gene_context_evidence': ('', 'gene_context_evidence', 'GeneContextEvidenceEpisode', 'gene_context_evidence/resource_work_submission')}
for _prefix in ('', 'gene_context_evidence/'):
    _parent = _prefix.rstrip('/')
    _portfolio = _prefix+'resource_work_submission'
    for _home, _ancestor, _role in SOURCE_CALLERS:
        CALLERS[_prefix+_home] = (_prefix+_ancestor if _ancestor else _parent,
                                  _role, 'LiteratureEpisode', _portfolio)
    for _home, _ancestor, _role in RESOURCE_CALLERS:
        CALLERS[_prefix+_home] = (_prefix+_ancestor if _ancestor else _parent,
                                  _role, 'ResourceEpisode', _portfolio)
    CALLERS[_prefix+'execution_progress_assessment'] = (_parent, 'monitor', 'MonitorEpisode', _portfolio)


def _original(registry):
    return registry.for_role('launch') if 'launch' in registry.roles else None


def _authentic(binding, home, registry):
    declared = CALLERS[home]
    return (getattr(binding, 'binding_path', None) == home
        and type(binding) is getattr(import_module(PACKAGE+'.'+home.replace('/', '.')+'.episode'),declared[2])
        and registry.for_binding_path(home) is binding
        and binding.roles == (declared[1],)
        and getattr(binding, 'commissioning_parent', None) == (declared[0] or 'legacy_annotation'))


def _possible_participant(registry,path):
    # Classify the full finite role graph without resolving an ambiguous first
    # source. An unknown suffix must reach the original Launch lookup even when
    # root/scientific literature or monitor sources share the first role.
    if not isinstance(path,(tuple,list)) or not path:
        return False
    homes={''};resource_frame=False
    for index,part in enumerate(path):
        if not isinstance(part,(tuple,list)) or not part or not isinstance(part[0],str):
            return resource_frame
        role=part[0]
        if index==0 and role=='annotation' and role not in registry.roles:
            continue
        if index==0:
            matches={home for home,row in CALLERS.items() if row[1]==role}
        else:
            matches={candidate for home in homes for candidate,row in CALLERS.items()
                     if row[0]==home and row[1]==role}
            matches.update(home for home in homes if home in CALLERS and CALLERS[home][1]==role)
        if not matches:
            return resource_frame or role in {'launch_api','launch_local','launch_hpc'}
        homes=matches
        resource_frame=resource_frame or any(CALLERS[home][2]=='ResourceEpisode' for home in homes)
    return True


def _declared_portfolio(registry, path):
    # Classify the entire finite role graph before validating invocation keys.
    # An unknown nonparticipant suffix does not acquire private authority just
    # because an earlier frame happens to be a literature/science caller.
    if not _possible_participant(registry,path):
        return None
    home, resource_frame = '', False
    for index, part in enumerate(path):
        if not isinstance(part,(tuple,list)) or not part or not isinstance(part[0],str):
            return CALLERS[home][3] if resource_frame else None
        role = part[0]
        if index==0 and role=='annotation' and role not in registry.roles:
            continue
        if index==0:
            if role not in {row[1] for row in CALLERS.values()}:
                return None
            # The registry's existing standalone lookup identifies this source,
            # never a different parent's Launch counterpart.
            home=getattr(registry.for_role(role),'binding_path',None)
            if home not in CALLERS:
                return None
        else:
            matches=[candidate for candidate,row in CALLERS.items()
                     if row[0]==home and row[1]==role]
            if not matches and home in CALLERS and CALLERS[home][1]==role:
                matches=[home]
            if len(matches)!=1:
                if role in {'launch_api','launch_local','launch_hpc'}:
                    return CALLERS[home][3] if home else 'resource_work_submission'
                return CALLERS[home][3] if resource_frame else None
            home=matches[0]
        resource_frame = resource_frame or CALLERS[home][2]=='ResourceEpisode'
    return CALLERS[home][3] if home else 'resource_work_submission'


def planning_binding(workflow, source, role):
    assert role == 'launch', 'Resource planning cannot select an HPC or received-result owner'
    registry = workflow.episode_bindings
    # A separately configured generic execution factory is a nonparticipant.
    # This check identifies exact registered Resource implementation homes,
    # never a global sole-role or merely available callback.
    resources = [home for home, row in CALLERS.items() if row[2]=='ResourceEpisode'
                 and home in registry._by_path]
    for candidate in resources:
        if not _authentic(registry._by_path[candidate],candidate,registry):
            raise ValueError('resource_planning_registered_identity_mismatch')
    if not resources:
        return _original(registry)
    supplied=getattr(source,'path',None)
    selected_portfolio=_declared_portfolio(registry,supplied)
    if selected_portfolio is None or not any(CALLERS[home][3]==selected_portfolio for home in resources):
        return _original(registry)
    path=tuple(tuple(part) if isinstance(part,(tuple,list)) else (part,) for part in supplied)
    malformed=any(len(part)!=2 or any(not isinstance(item,str) or not item for item in part) for part in path)
    if malformed:
        raise ValueError('episode_binding_runtime_path_required')
    parent, home, prefix, portfolio = None, '', (), 'resource_work_submission'
    for index, (selected_role, key) in enumerate(path):
        prefix = path[:index+1]
        if index==0 and selected_role=='annotation' and selected_role not in registry.roles:
            continue
        if index==0:
            actual=registry.for_role(selected_role)
            expected=getattr(actual,'binding_path',None)
            if expected not in CALLERS:
                return _original(registry)
            if not _authentic(actual,expected,registry):
                raise ValueError('resource_planning_private_edge_mismatch')
            parent,home,portfolio=actual,expected,CALLERS[expected][3]
            continue
        matches = [candidate for candidate, row in CALLERS.items()
                   if row[0]==home and row[1]==selected_role]
        if home=='gene_context_evidence' and selected_role=='gene_context_evidence':
            matches = ['gene_context_evidence']
        if home and CALLERS[home][2]=='MonitorEpisode' and selected_role=='monitor':
            matches = [home]
        if not matches:
            # Once a concrete Resource owner was selected, a broken/foreign
            # edge cannot turn into an unrelated global planning portfolio.
            if home and CALLERS[home][2]=='ResourceEpisode':
                registry.for_path(prefix)
                raise ValueError('resource_planning_context_not_declared')
            # Malformed direct native edges in this finite family retain the
            # original registry's exact private-parent failure.
            if selected_role in {'launch_api','launch_local','launch_hpc'}:
                registry.for_path(prefix)
                raise ValueError('resource_planning_context_not_declared')
            return _original(registry)
        assert len(matches)==1
        expected = matches[0]
        declared=(workflow.declared_child_roles('annotation',path=path[:1]) if parent is None
                  else parent.child_roles(CALLERS[home][1]))
        if selected_role not in declared:
            raise ValueError('resource_planning_child_not_declared:'+expected)
        actual = registry._child_binding(parent, selected_role)
        if not _authentic(actual, expected, registry):
            # The finite caller graph and this portfolio's Resource footprint
            # already selected this participant. A wrong implementation cannot
            # turn the broken incoming edge into global sibling authority.
            raise ValueError('resource_planning_private_edge_mismatch')
        parent, home, portfolio = actual, expected, CALLERS[expected][3]
    # Authenticate the saved entire graph before selecting its declared root or
    # scientific Resource portfolio. Recursive science uses its last real frame.
    if not any(CALLERS[candidate][3]==portfolio for candidate in resources):
        return _original(registry)
    if home:
        assert registry.for_path(path) is parent
    assert portfolio==selected_portfolio
    if home==portfolio:
        # A standalone actual Launch is its own source, not a sibling selected
        # from a unique role. The full registered identity was checked above.
        return parent
    if portfolio.startswith('gene_context_evidence/'):
        positions = [index for index,(selected_role,_) in enumerate(path) if selected_role=='gene_context_evidence']
        if not positions:
            raise ValueError('resource_planning_scientific_parent_required')
        parent_path=path[:positions[-1]+1]
        owner=registry.for_path(parent_path)
        assert _authentic(owner,'gene_context_evidence',registry)
        declared=owner.child_roles('gene_context_evidence')
    else:
        if path[0][0]!='annotation':
            raise ValueError('resource_planning_annotation_parent_required')
        parent_path=path[:1]
        declared=workflow.declared_child_roles('annotation',path=parent_path)
    if 'launch' not in declared:
        raise ValueError('resource_planning_launch_not_declared')
    selected=registry.for_child(parent_path,'launch')
    if not _authentic(selected,portfolio,registry):
        raise ValueError('resource_planning_private_portfolio_mismatch')
    return selected
