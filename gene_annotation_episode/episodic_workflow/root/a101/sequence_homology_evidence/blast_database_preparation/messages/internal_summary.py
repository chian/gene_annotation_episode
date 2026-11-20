"""Where the preparation stands, as a pure function of the view: the commission (the parent input), what each
child reported, the handoff and plan references a launch returned, the prepared-data references a results child
returned, which of those are usable and the latest finding on the product. The references are records this episode
holds because its children returned them."""


def internal_summary(view):
    parent = view.parent_input
    launches, results = [], []
    for unit in view.outcomes:
        if unit['kind'] == 'tool':
            continue
        (launches if unit['slot'] == 'launch_local' else results).append(unit['report'])
    handoff_refs, plan_refs, prepared_refs, usable_refs = [], [], [], []
    for report in launches:
        if report['completed']:
            handoff_refs.extend(ref for ref in report['handoff_refs'] if ref not in handoff_refs)
            plan_refs.extend(ref for ref in report['plan_refs'] if ref not in plan_refs)
    for report in results:
        prepared_refs.extend(ref for ref in report['prepared_refs'] if ref not in prepared_refs)
        if report['finding']['usable']:
            usable_refs.extend(ref for ref in report['prepared_refs'] if ref not in usable_refs)
    return {**parent, 'launches': launches, 'results': results, 'handoff_refs': handoff_refs,
            'plan_refs': plan_refs, 'prepared_refs': prepared_refs, 'usable_prepared_refs': usable_refs,
            'latest_finding': results[-1]['finding'] if results else None}
