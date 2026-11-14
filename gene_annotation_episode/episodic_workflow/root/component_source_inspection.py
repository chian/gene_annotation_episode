"""Reuse this episode's received source operands without new work or credit.

The journal remains authoritative. This is a read-only decision view of actual
own outcomes, never a scientific assessment or a view into a child's history.
"""
from copy import deepcopy
import json


VERSION = 'component_axis_source_inspection_v1'
POPULATIONS = {'literature.partner.populate', 'literature.partner.source.populate',
    'literature.reaction.populate', 'literature.reaction.source.populate'}


def _merge(spans):
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1]['end']:
            merged[-1]['end'] = max(end, merged[-1]['end'])
        else:
            merged.append({'start': start, 'end': end})
    return merged


def inspection_index(store, *, run_id, episode_id, known_source_refs):
    """Group actual returned byte ranges, witnesses and saved component results.

    Immutable artifact identity keeps coordinate frames separate. A result is
    shown only for this episode and run, and an actually received source. A
    completed read is inspection, not proof that a biological question is done.
    """
    known = set(known_source_refs)
    reads, searches, populations = {}, {}, {}
    rows = store.db.execute('SELECT decision_index,action,result FROM runtime_actions '
        'WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY decision_index',
        (run_id, episode_id))
    for row in rows:
        action, outcome = json.loads(row['action']), json.loads(row['result'])
        tool, args = action.get('tool'), action.get('arguments', {})
        if tool not in {'source.read', 'source.locate', *POPULATIONS}:
            continue
        if outcome.get('status') != 'completed' or args.get('source_ref') not in known:
            continue
        result = outcome.get('result')
        if not isinstance(result, dict):
            continue
        index = row['decision_index']
        if tool == 'source.read':
            start, end = result.get('start'), result.get('end')
            if type(start) is not int or type(end) is not int or not 0 <= start <= end:
                continue
            key = (result.get('source_ref'), result.get('artifact_ref'))
            if not all(isinstance(ref, str) for ref in key):
                continue
            entry = reads.setdefault(key, {'source_ref': key[0], 'artifact_ref': key[1],
                'status': 'read_completed', 'representations': set(),
                'spans': [], 'decision_indices': []})
            if end > start:
                entry['spans'].append((start, end))
            entry['decision_indices'].append(index)
            if isinstance(result.get('representation'), str):
                entry['representations'].add(result['representation'])
        elif tool == 'source.locate':
            key = (args['source_ref'], args.get('representation'), args.get('needle'),
                result.get('artifact_ref'))
            entry = searches.setdefault(key, {'source_ref': key[0],
                'representation': key[1], 'needle': key[2], 'artifact_ref': key[3],
                'decision_indices': [], 'matches': {}, 'search_ranges': [],
                'status': 'search_attempts_recorded', 'last_query_has_more': result.get('has_more')})
            entry['decision_indices'].append(index)
            entry['last_query_has_more'] = result.get('has_more')
            entry['next_query'] = deepcopy(result.get('next_query'))
            span = result.get('scanned_range')
            if isinstance(span, dict) and all(type(span.get(k)) is int for k in ('start', 'end')):
                entry['search_ranges'].append((span['start'], span['end']))
            for match in result.get('matches', ()):
                witness = match.get('witness')
                if not isinstance(witness, dict):
                    continue
                # Keep exact returned quotations and context, including their
                # original byte frames. Never reconstruct a quote from a label.
                saved = {k: deepcopy(match[k]) for k in ('artifact_ref', 'witness', 'context')
                    if k in match}
                entry['matches'][json.dumps(saved, sort_keys=True)] = saved
        else:
            sheet = result.get('sheet_ref')
            if not isinstance(sheet, str):
                continue
            entry = populations.setdefault(sheet, {'sheet_ref': sheet,
                'operation': tool, 'status': 'component_result_saved', 'decision_indices': []})
            entry['decision_indices'].append(index)
            entry.update({key: deepcopy(result[key]) for key in (
                'cells', 'assay_interpretation', 'experiment_assessment', 'ratio_kind',
                'ratio_mode', 'ratio_unit', 'ratio_origin', 'independent_n',
                'reported_sample_sd', 'ratio_uncertainty', 'operand_source_kind') if key in result})
    if not (reads or searches or populations):
        return None
    for entry in populations.values():
        assessment = entry.get('experiment_assessment')
        revised = assessment.get('revises_sheet_ref') if isinstance(assessment, dict) else None
        if revised in populations:
            populations[revised].setdefault('superseded_by_own_result_refs', []).append(entry['sheet_ref'])
    return {'version': VERSION, 'receiving_episode_id': episode_id,
        'meaning': 'Already received own operands, not additional evidence or credit. '
            'Inspected bytes do not establish that every question about them is answered. '
            'An unavailable component records the selected operands, not absence from an entire source. '
            'Saved results retain their explicit revision links; consult current per-use qualifications before reuse.',
        'read_sources': [{**{k: v for k, v in entry.items() if k not in {'spans', 'representations'}},
            'representations': sorted(entry['representations']),
            'inspected_ranges': _merge(entry['spans'])} for entry in reads.values()],
        'located_passages': [{**{k: v for k, v in entry.items() if k not in {'matches', 'search_ranges'}},
            'matches': list(entry['matches'].values()),
            'scanned_ranges': _merge(entry['search_ranges'])} for entry in searches.values()],
        'saved_component_results': list(populations.values()),
        'exact_prior_outcomes': 'episode.history with view=records and the selected decision_indices',
        'credit_change': False, 'permission_change': False}
