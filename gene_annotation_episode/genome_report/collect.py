"""The report's data, read from the files a finished run leaves: its journal and its workspace.

``collect(workspace, journal, run_id)`` opens both read-only, takes the root's return from the closed run, the records
of the workspace and the units of the journal, and gives one plain dictionary (``assemble``). The pages draw from that
dictionary and from nothing else. Nothing here imports episode code or writes anywhere.

Positions are zero-based and half-open, on the sequence, as the records hold them. The report shows evidence, not
scores: a score of the root's return is read only to order lines and to say whether a call is contested.

The dictionary::

    run          run_id, entry, ended_by, units, episodes
    sequences    per sequence of the scope: ref, name, length, molecule, gc_fraction
    organism     leader_taxon_id, rival_taxon_id, agreed_taxon_id
                 candidates   taxon_id, name, rank_code, role (leader, rival, other),
                              lineage [taxon_id, name]
                 assignments  per taxon a classifier assigned: tool, database, version, taxon_id, name, count,
                              model_score
    features     every feature call, by sequence and position:
                 id (F1, F2, ...), feature_ref, sequence_ref, kind, strand, segments, start, end, length
                 frame        1 to 3 on the strand, signed by strand; None for a feature that is not read in codons
                 chosen       whether it is part of the genome annotation
                 lost_to      id of the chosen rival it lost to
                 parent       id of the smallest feature that contains it
                 versions     every position called for it: start, end, segments
                 rivals       id, shared_letters, same_type, same_strand, same_frame
                 protein      ref, length (residues); None when it has none
                 standing     supported, contested, no_annotation
                 call         the annotation line chosen for it; None when none is
                 alternates   the other annotation lines on it, the best first
                              line: vocabulary, name, identifier, names (every name on the line), status,
                                    hit_count, best_identity, median_feature_coverage, axes [axis, status],
                                    claims [predicate, partner, partner_kind, commissions]
                 hits         the best matches inside it (HITS_SHOWN at most): tool, database, version, accession,
                              label, reference_type, reference_length, identity, feature_coverage (the share
                              of the feature's letters the match lies on), target_coverage,
                              evalue, bitscore, start, end (on the sequence), reference_start, reference_end,
                              taxon_id, taxon_name, line (call, alternate, other)
                 hit_count    every match inside it
                 names        per name among all its matches: label, count, best_identity, median_feature_coverage,
                              line (call, alternate, other)
                 hit_taxa     taxon_id, name, count
                 profile_matches  accession, name, start, end (on the sequence), evalue, bitscore, model_coverage
                 searches     per search that could have found it: tool, database, version, hit_count
    searches     every search the run made: episode, tool, database, version, operand (sequence or feature id),
                 finds (the kinds of observation its tool makes), observation_count
    failures     every unit that did not complete: episode, tool, status, failure_code
    not_tried    per episode, the tools it was offered and never chose: episode, tools
    episodes     binding_path, ended_by, units
    provenance   journal, tools [provider, database, version, sources, observations], record_counts
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from statistics import median

HITS_SHOWN = 60
# A call is contested when an alternate line's score is at least this share of the call's own.
CONTESTED_SHARE = 0.5


def _read_only(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return sqlite3.connect(f'file:{path}?mode=ro', uri=True)


def collect(workspace, journal, run_id):
    """The report's data of the closed run ``run_id``."""
    workspace = Path(workspace)
    with _read_only(journal) as record, _read_only(workspace / 'state.sqlite3') as store:
        run = record.execute('SELECT state, result FROM runs WHERE run_id=?', (run_id,)).fetchone()
        if run is None:
            raise ValueError('genome_report_run_not_recorded:' + run_id)
        if run[0] != 'closed':
            raise ValueError('genome_report_run_not_closed:' + run_id)
        episodes = [{'path': json.loads(path), 'binding_path': binding_path, 'completion': json.loads(completion)}
                    for path, binding_path, completion in record.execute(
                        'SELECT path, binding_path, completion FROM episodes WHERE run_id=? AND state=? '
                        'ORDER BY rowid', (run_id, 'closed'))]
        units = [{'path': json.loads(path), 'label': label, 'outcome': json.loads(outcome)}
                 for path, label, outcome in record.execute(
                     'SELECT path, label, outcome FROM units WHERE run_id=? ORDER BY path, unit_index', (run_id,))]
        offered = [{'path': json.loads(path), 'offered': json.loads(offer),
                    'chosen': None if chosen is None else json.loads(chosen)}
                   for path, offer, chosen in record.execute(
                       'SELECT path, offered, chosen FROM ceilings WHERE run_id=? ORDER BY path, unit_index',
                       (run_id,))]
        (identity,) = record.execute('SELECT identity FROM journal').fetchone()
        records = {ref: json.loads(data) for ref, data in store.execute('SELECT id, data FROM records')}
        records.update((ref, json.loads(data)) for ref, data in store.execute('SELECT id, data FROM inputs'))
    return assemble(run_id=run_id, journal=identity, result=json.loads(run[1]), episodes=episodes, units=units,
                    offered=offered, records=records, sequence_text=lambda ref: _artifact(workspace, ref))


def _artifact(workspace, ref):
    digest = ref.removeprefix('artifact_')
    return (workspace / 'artifacts' / digest[:2] / digest).read_text()


def assemble(*, run_id, journal, result, episodes, units, offered, records, sequence_text):
    finding = result['finding']
    by_type = {}
    for record in records.values():
        by_type.setdefault(record['record_type'], []).append(record)
    taxon_names = {record['accession']: record['label'] for record in by_type.get('reference', ())
                   if record['reference_type'] == 'taxon'}
    produced_by = _produced_by(units)
    sequences = [_sequence(records[target['target_ref'][0]], sequence_text) for target in finding['feature_calls']]
    features = _features(finding, records, by_type)
    matches = _matches(by_type, records, taxon_names, produced_by)
    searches = _searches(by_type, records, produced_by, features)
    for feature in features:
        _evidence(feature, matches, searches, finding)
    entry = episodes[0]
    return {
        'run': {'run_id': run_id, 'entry': entry['binding_path'], 'ended_by': entry['completion']['ended_by'],
                'units': len(units), 'episodes': len(episodes)},
        'sequences': sequences,
        'organism': _organism(finding['organism'], by_type, records, taxon_names),
        'features': features,
        'searches': [{name: search[name] for name in ('episode', 'tool', 'database', 'version', 'operand', 'finds',
                                                      'observation_count')} for search in searches],
        'failures': [{'episode': _episode(unit['path']), 'tool': _tool_of_label(unit['label']),
                      'status': unit['outcome']['outcome']['status'],
                      'failure_code': unit['outcome']['outcome'].get('failure_code')}
                     for unit in units if unit['outcome']['kind'] == 'tool'
                     and unit['outcome']['outcome']['status'] != 'completed'
                     and _tool_of_label(unit['label']) != 'hold'],
        'not_tried': _not_tried(offered),
        'episodes': [{'binding_path': episode['binding_path'], 'ended_by': episode['completion']['ended_by'],
                      'units': episode['completion']['units']} for episode in episodes],
        'provenance': {'journal': journal, 'tools': _tools(by_type, records),
                       'record_counts': {kind: len(rows) for kind, rows in sorted(by_type.items())}},
    }


# -- the sequence, the organism ----------------------------------------------------------------------------------------

def _sequence(record, sequence_text):
    letters = sequence_text(record['sequence_ref']).upper()
    return {'ref': record['id'], 'name': record['name'], 'length': record['length'], 'molecule': record['molecule'],
            'gc_fraction': (letters.count('G') + letters.count('C')) / len(letters)}


def _tool(source):
    """The name, database and version of the tool behind a source record, as the record gives them."""
    provider, version = source['provider'], source.get('version')
    parts = provider.split('.')
    if parts[0] == 'native':
        name = parts[1]
    elif version and re.fullmatch(r'T?BLAST[NPX] .+', version):
        name, version = version.split(' ', 1)
        name = name.lower()
    else:
        name = provider
    return {'tool': name, 'database': source.get('accession'), 'version': version}


def _organism(organism, by_type, records, taxon_names):
    role = {organism.get('leader_taxon_id'): 'leader', organism.get('rival_taxon_id'): 'rival'}
    assignments = []
    for observation in by_type.get('observation', ()):
        if observation['kind'] != 'taxonomy_assignment':
            continue
        measured = _measurements(observation)
        taxon = records[measured['reference_ref']]
        assignments.append({**_tool(records[observation['source_ref']]), 'taxon_id': int(taxon['accession']),
                            'name': taxon['label'], 'count': measured.get('count'),
                            'model_score': measured.get('model_score')})
    assignments.sort(key=lambda row: (row['tool'], row['database'] or '', row['taxon_id']))
    return {
        'leader_taxon_id': organism.get('leader_taxon_id'), 'rival_taxon_id': organism.get('rival_taxon_id'),
        'agreed_taxon_id': organism.get('agreed_taxon_id'),
        'candidates': [{'taxon_id': row['taxon_id'], 'name': row['name'], 'rank_code': row['rank_code'],
                        'role': role.get(row['taxon_id'], 'other'),
                        'lineage': [{'taxon_id': step['taxon_id'], 'name': taxon_names.get(str(step['taxon_id']))}
                                    for step in row['lineage']]}
                       for row in organism['candidates']],
        'assignments': assignments,
    }


# -- the feature calls -------------------------------------------------------------------------------------------------

def _features(finding, records, by_type):
    genome = {line['feature_call']['feature_refs'][0]: line for line in finding['genome_annotation']['feature_calls']}
    proteins = {parent: product for product in by_type.get('product', ()) if product['molecule'] == 'protein'
                for parent in product['parent_refs']}
    features = []
    for target in finding['feature_calls']:
        sequence = records[target['target_ref'][0]]
        ranked = [call['feature_refs'][0] for call in target['features']]
        for call in target['features']:
            ref = call['feature_refs'][0]
            protein = proteins.get(ref)
            features.append({
                'feature_ref': ref, 'sequence_ref': sequence['id'], 'kind': call['kind'], 'strand': call['strand'],
                'segments': call['segments'], 'start': call['start'], 'end': call['end'],
                'length': sum(segment['end'] - segment['start'] for segment in call['segments']),
                'frame': _frame(call, sequence['length']) if protein else None,
                'chosen': genome[ref]['chosen'], 'lost_to': (genome[ref].get('lost_to') or [None])[0],
                'versions': [{name: version[name] for name in ('start', 'end', 'segments')}
                             for version in call['versions']],
                'rivals': [{'id': ranked[rival['rank']], **{name: rival[name] for name in (
                    'shared_letters', 'same_type', 'same_strand', 'same_frame')}} for rival in call['rivals']],
                'protein': None if protein is None else {'ref': protein['id'],
                                                         'length': protein['mapping']['symbol_length']},
                '_path': None if protein is None else protein['mapping']['path'],
                '_chosen_annotation': genome[ref].get('annotation'),
            })
    features.sort(key=lambda feature: (feature['sequence_ref'], feature['start'], -feature['end']))
    ids = {}
    for number, feature in enumerate(features, 1):
        feature['id'] = ids[feature['feature_ref']] = 'F%d' % number
    for feature in features:
        feature['lost_to'] = ids.get(feature['lost_to'])
        for rival in feature['rivals']:
            rival['id'] = ids[rival['id']]
        holders = [other for other in features if other is not feature
                   and other['sequence_ref'] == feature['sequence_ref'] and other['strand'] == feature['strand']
                   and other['start'] <= feature['start'] and feature['end'] <= other['end']
                   and other['length'] > feature['length']]
        feature['parent'] = min(holders, key=lambda other: other['length'])['id'] if holders else None
    return features


def _frame(call, sequence_length):
    if call['strand'] == '-':
        return -((sequence_length - call['end']) % 3 + 1)
    return call['start'] % 3 + 1


# -- the matches -------------------------------------------------------------------------------------------------------

def _measurements(observation):
    return {measurement['name']: measurement['value'].get('value', measurement['value'].get('ref'))
            for measurement in observation['measurements']}


def _taxon_of(accession):
    """The taxon a BV-BRC feature accession names (``<taxon id>.<genome number>.<type>.<number>``), else None."""
    found = re.fullmatch(r'(\d+)\.\d+\.[A-Za-z_]+\.\d+', accession or '')
    return int(found.group(1)) if found else None


def _on_sequence(path, start, end):
    """The stretch of the sequence that residues ``start`` to ``end`` of a translated product lie on."""
    def letter(offset):
        for step in path:
            size = step['end'] - step['start']
            if offset < size:
                return step['start'] + offset if step['strand'] != '-' else step['end'] - 1 - offset
            offset -= size
        raise ValueError('genome_report_residue_outside_its_product')
    first, last = letter(start * 3), letter(end * 3 - 1)
    return min(first, last), max(first, last) + 1


def _matches(by_type, records, taxon_names, produced_by):
    """Every comparison and profile match of the workspace, placed on the sequence."""
    matches = []
    for observation in by_type.get('observation', ()):
        if observation['kind'] not in ('comparison', 'profile_match'):
            continue
        measured = _measurements(observation)
        reference = records[measured['reference_ref']]
        source = records[observation['source_ref']]
        subject = records[observation['subject_refs'][0]]
        spans = {role: [interval for interval in observation.get('operand_intervals', ())
                        if interval['role'] == role] for role in ('query', 'reference')}
        query_start = min(interval['start'] for interval in spans['query'])
        query_end = max(interval['end'] for interval in spans['query'])
        native = observation.get('native_blast', {})
        if subject['record_type'] == 'product':
            start, end = _on_sequence(subject['mapping']['path'], query_start, query_end)
            sequence_ref, strand = subject['mapping']['path'][0]['subject_ref'], subject['mapping']['path'][0]['strand']
        else:
            start, end, sequence_ref = query_start, query_end, subject['id']
            frame = native.get('query_frame')
            strand = ('-' if frame < 0 else '+') if frame else {'Plus': '+', 'Minus': '-'}.get(native.get('query_strand'))
        taxon = _taxon_of(reference['accession'])
        tool = _tool(source)
        unit = produced_by.get(source['id'])
        if unit is not None and tool['database'] is None:
            tool['database'] = unit['database']
        matches.append({
            'kind': observation['kind'], **tool, 'source_ref': source['id'], 'subject_ref': subject['id'],
            'sequence_ref': sequence_ref, 'strand': strand, 'start': start, 'end': end,
            'accession': reference['accession'], 'label': reference['label'],
            'reference_ref': reference['id'], 'reference_type': reference['reference_type'],
            'reference_length': reference.get('length') or measured.get('model_length'),
            'identity': measured.get('identity_fraction', measured.get('alignment_identity_fraction')),
            'query_coverage': measured.get('query_coverage', measured.get('paired_sequence_coverage')),
            'target_coverage': measured.get('target_coverage', measured.get('paired_model_coverage')),
            'evalue': measured['evalue'], 'bitscore': measured['bitscore'],
            'reference_start': min((interval['start'] for interval in spans['reference']), default=None),
            'reference_end': max((interval['end'] for interval in spans['reference']), default=None),
            'taxon_id': taxon, 'taxon_name': taxon_names.get(str(taxon)),
        })
    return matches


def _inside(match, feature):
    """Whether a match belongs to a feature: it was made with the feature's own protein, or it was made with the
    sequence and at least half of it lies in the feature, on the feature's strand."""
    if feature['protein'] is not None and match['subject_ref'] == feature['protein']['ref']:
        return True
    if match['subject_ref'] != feature['sequence_ref']:
        return False
    if match['strand'] is not None and feature['strand'] in '+-' and match['strand'] != feature['strand']:
        return False
    shared = sum(max(0, min(match['end'], segment['end']) - max(match['start'], segment['start']))
                 for segment in feature['segments'])
    return 2 * shared >= match['end'] - match['start']


def _line(annotation, claims):
    names = list(dict.fromkeys(name for name in [annotation.get('name'), *(member.get('name') for member in
                                                                            annotation['members'])] if name))
    identifiers = {value for value in [annotation.get('identifier'), *(member.get('identifier') for member in
                                                                        annotation['members'])] if value}
    return {'vocabulary': annotation['vocabulary'], 'name': annotation.get('name'),
            'identifier': annotation.get('identifier'), 'names': names, 'status': annotation['status'],
            'axes': [{'axis': row['axis'], 'status': row['status']} for row in annotation['rows']],
            'claims': [{name: claim[name] for name in ('predicate', 'partner', 'partner_kind', 'commissions')}
                       for claim in claims
                       if all(claim['annotation'].get(name) == annotation.get(name)
                              for name in ('vocabulary', 'name', 'identifier'))],
            '_identifiers': identifiers, '_score': annotation.get('score')}


def _on_line(match, line):
    return match['label'] in line['names'] or bool({match['accession'], match['reference_ref']} & line['_identifiers'])


def _summary(matches):
    return {'hit_count': len(matches),
            'best_identity': max((match['identity'] for match in matches if match['identity'] is not None),
                                 default=None),
            'median_feature_coverage': median(match['feature_coverage'] for match in matches) if matches else None}


def _evidence(feature, matches, searches, finding):
    """Attach to a feature its annotation lines and the matches that lie inside it. A match's ``feature_coverage`` is
    the share of the feature's letters it lies on."""
    inside = [{**match, 'feature_coverage': sum(
        max(0, min(match['end'], segment['end']) - max(match['start'], segment['start']))
        for segment in feature['segments']) / feature['length']} for match in matches if _inside(match, feature)]
    lines = [_line(annotation, finding['claims']) for annotation in finding['annotations']
             if annotation['feature_call']['feature_ref'] == feature['feature_ref']]
    chosen = feature.pop('_chosen_annotation')
    feature.pop('_path')
    call = None
    if chosen is not None:
        (call,) = [line for line in lines if all(line[name] == chosen.get(name)
                                                 for name in ('vocabulary', 'name', 'identifier'))]
    alternates = [line for line in lines if line is not call]

    def of(match):
        if call is not None and _on_line(match, call):
            return 'call'
        return 'alternate' if any(_on_line(match, line) for line in alternates) else 'other'
    for line in lines:
        line.update(_summary([match for match in inside if _on_line(match, line)]))
    if call is None:
        feature['standing'] = 'no_annotation'
    elif any(line['_score'] is not None and call['_score'] and line['_score'] >= CONTESTED_SHARE * call['_score']
             for line in alternates):
        feature['standing'] = 'contested'
    else:
        feature['standing'] = 'supported'
    feature['call'], feature['alternates'] = call, alternates
    compared = sorted((match for match in inside if match['kind'] == 'comparison'),
                      key=lambda match: (-match['bitscore'], match['accession']))
    shown = ('tool', 'database', 'version', 'accession', 'label', 'reference_type', 'reference_length', 'identity',
             'feature_coverage', 'target_coverage', 'evalue', 'bitscore', 'start', 'end', 'reference_start',
             'reference_end', 'taxon_id', 'taxon_name')
    feature['hits'] = [{**{name: match[name] for name in shown}, 'line': of(match)} for match in compared[:HITS_SHOWN]]
    feature['hit_count'] = len(compared)
    by_label = {}
    for match in compared:
        by_label.setdefault(match['label'], []).append(match)
    feature['names'] = sorted(({'label': label, **{key: value for key, value in _summary(group).items()
                                                   if key != 'hit_count'},
                                'count': len(group), 'line': of(group[0])} for label, group in by_label.items()),
                              key=lambda row: (-row['count'], row['label']))
    taxa = {}
    for match in compared:
        if match['taxon_id'] is not None:
            taxa.setdefault((match['taxon_id'], match['taxon_name']), []).append(match)
    feature['hit_taxa'] = sorted(({'taxon_id': taxon, 'name': name, 'count': len(group)}
                                  for (taxon, name), group in taxa.items()),
                                 key=lambda row: (-row['count'], row['taxon_id']))
    feature['profile_matches'] = sorted(
        ({'accession': match['accession'], 'name': match['label'], 'start': match['start'], 'end': match['end'],
          'evalue': match['evalue'], 'bitscore': match['bitscore'], 'model_coverage': match['target_coverage']}
         for match in inside if match['kind'] == 'profile_match'), key=lambda row: (row['start'], row['accession']))
    feature['searches'] = [
        {'tool': search['tool'], 'database': search['database'], 'version': search['version'],
         'hit_count': sum(match['source_ref'] == search['source_ref'] for match in inside)}
        for search in searches
        if {'comparison', 'profile_match'} & set(search['finds'])
        and (search['operand_ref'] == feature['sequence_ref']
             or (feature['protein'] is not None and search['operand_ref'] == feature['protein']['ref']))]
    for line in lines:
        del line['_identifiers'], line['_score']


# -- what the run did --------------------------------------------------------------------------------------------------

def _episode(path):
    return '/'.join(step[0].split('__')[-1] for step in path[1:]) or path[0][0]


def _tool_of_label(label):
    """``tool:<name>:<position>`` is a tool's unit; anything else is a child's."""
    parts = label.split(':')
    return parts[1] if parts[0] == 'tool' else None


def _produced_by(units):
    """Per record a unit changed: the episode of the unit, its tool and the database it named. The database of a
    search an episode's child made is the one its parent commissioned it with."""
    commissioned = {}
    for unit in units:
        if unit['outcome']['kind'] == 'child':
            commissioned[tuple(map(tuple, unit['path'])), unit['label']] = unit['outcome']['arguments']
    produced = {}
    for unit in units:
        if unit['outcome']['kind'] != 'tool':
            continue
        arguments = unit['outcome']['arguments']
        path = tuple(map(tuple, unit['path']))
        parent = commissioned.get((path[:-1], path[-1][1]), {})
        request = arguments.get('request', {})
        database = (arguments.get('database') or arguments.get('index') or request.get('database')
                    or parent.get('database'))
        outcome = unit['outcome']['outcome']
        for ref in outcome.get('changed_record_refs') or outcome.get('record_refs') or ():
            produced.setdefault(ref, {'episode': _episode(unit['path']), 'tool': _tool_of_label(unit['label']),
                                      'database': database})
    return produced


def _searches(by_type, records, produced_by, features):
    """Every source a tool of the run made by looking something up or comparing: those that hold a comparison, a
    profile match or a taxonomy assignment, and those of the same tools that hold none."""
    counts, finds = {}, {}
    for observation in by_type.get('observation', ()):
        counts[observation['source_ref']] = counts.get(observation['source_ref'], 0) + 1
        finds.setdefault(records[observation['source_ref']]['provider'], set()).add(observation['kind'])
    by_operand = {feature['protein']['ref']: feature['id'] for feature in features if feature['protein']}
    searches = []
    for source in by_type.get('source', ()):
        if source['provider'] not in finds or not source.get('operand_refs'):
            continue
        tool = _tool(source)
        unit = produced_by.get(source['id'], {})
        operand = source['operand_refs'][0]
        searches.append({'episode': unit.get('episode'), **tool,
                         'database': tool['database'] or unit.get('database'),
                         'operand': by_operand.get(operand, 'sequence' if operand.startswith('input_') else operand),
                         'operand_ref': operand, 'source_ref': source['id'],
                         'finds': sorted(finds[source['provider']]),
                         'observation_count': counts.get(source['id'], 0)})
    searches.sort(key=lambda row: (row['episode'] or '', row['tool'], row['database'] or '', row['source_ref']))
    return searches


def _not_tried(offered):
    by_episode = {}
    for decision in offered:
        entry = by_episode.setdefault(_episode(decision['path']), {'offered': set(), 'chosen': set()})
        entry['offered'].update(decision['offered'])
        if decision['chosen'] is not None:
            entry['chosen'].add(decision['chosen']['action_type'])
    return [{'episode': episode, 'tools': sorted(entry['offered'] - entry['chosen'])}
            for episode, entry in sorted(by_episode.items()) if entry['offered'] - entry['chosen']]


def _tools(by_type, records):
    counts = {}
    for observation in by_type.get('observation', ()):
        counts[observation['source_ref']] = counts.get(observation['source_ref'], 0) + 1
    tools = {}
    for source in by_type.get('source', ()):
        if source['provider'] == 'caller':
            continue
        key = (source['provider'], source.get('accession'), source.get('version'))
        row = tools.setdefault(key, {'provider': key[0], 'database': key[1], 'version': key[2], 'sources': 0,
                                     'observations': 0})
        row['sources'] += 1
        row['observations'] += counts.get(source['id'], 0)
    return [tools[key] for key in sorted(tools, key=lambda key: tuple(part or '' for part in key))]
