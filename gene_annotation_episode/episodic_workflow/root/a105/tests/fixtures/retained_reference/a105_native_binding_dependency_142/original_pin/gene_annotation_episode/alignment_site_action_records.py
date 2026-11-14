"""Read exact selected own site-operation results for parent-requested facts.

No calculator, model, native execution, new journal, observation or credit is
used here. Closed facts are compared to their original saved values on return.
"""
from __future__ import annotations

import json

from .alignment_site_native import (immutable_record, operand_descriptor,
    original_mappings, paf_row_bytes, source_descriptor, read_quality, biopython_molecule,
    reference_source_operands)
from .communication import plain
from .domain import canonical, identity
from .episode_return_records import EpisodeReturnRecords
from .tool_grading_artifacts import MEDIA_TYPE, SCHEMA


TOOLS = {'reference_site_rows': 'sequence.sites', 'blast_hsp_column_rows': 'result.blast.hsp'}


class AlignmentSiteActionRecords(EpisodeReturnRecords):
    def __init__(self, store, run_id, *, sequence_reader):
        super().__init__(store, run_id, failure_prefix='alignment_site_return_')
        self.sequence_reader = sequence_reader

    def _context(self, context):
        self.authenticate(context)
        self._require(context.role == 'scientific_process', 'scientific_owner_required')

    def _requested(self, context):
        from .alignment_site_returns import requested_site_projections
        return requested_site_projections(plain(context.request)['report_contract']['measurements']['schema'])

    def own_action_results(self, context, *, source, selection, after_decision_index, limit):
        self._context(context)
        requested = self._requested(context)
        self._require(source in TOOLS and source in requested, 'requested_source_required')
        self._require(self._equal(selection, requested[source]['selection']), 'selection_conflict')
        self._require(type(limit) is int and limit > 0 and
            (after_decision_index is None or type(after_decision_index) is int and after_decision_index >= 0),
            'explicit_page_required')
        arguments = [self.run_id, context.episode_id,
                     -1 if after_decision_index is None else after_decision_index, TOOLS[source]]
        predicates = []
        if selection['alignment_refs'] is not None:
            name = 'alignment_ref' if source == 'reference_site_rows' else 'observation_ref'
            predicates.append(f"json_extract(a.action,'$.arguments.{name}') IN (SELECT value FROM json_each(?))")
            arguments.append(canonical(selection['alignment_refs']))
        if selection['window'] is not None:
            for key, value in selection['window'].items():
                prefix = 'window.' if source == 'reference_site_rows' else ''
                predicates.append(f"json_extract(a.action,'$.arguments.{prefix}{key}')=?")
                arguments.append(value)
        if selection['positions'] is not None:
            predicates.extend([
                "json_type(a.action,'$.arguments.positions')='array'",
                "NOT EXISTS(SELECT DISTINCT value FROM json_each(a.action,'$.arguments.positions') "
                "EXCEPT SELECT value FROM json_each(?))",
                "NOT EXISTS(SELECT value FROM json_each(?) EXCEPT SELECT DISTINCT value "
                "FROM json_each(a.action,'$.arguments.positions'))",
            ])
            arguments.extend([canonical(selection['positions'])] * 2)
        query = """SELECT a.decision_index, a.action, a.result AS runtime_result,
            t.operation_key,t.id,t.name,t.arguments,t.scope,t.result AS tool_result
            FROM runtime_actions a LEFT JOIN tool_operations t
              ON t.operation_key=a.run_id||':'||a.episode_id||':'||a.decision_index
            WHERE a.run_id=? AND a.episode_id=? AND a.decision_index>?
              AND json_extract(a.action,'$.kind')='tool'
              AND json_extract(a.action,'$.tool')=?
              AND json_extract(a.result,'$.status') IN ('completed','partial')"""
        if predicates:
            query += ' AND ' + ' AND '.join(predicates)
        query += ' ORDER BY a.decision_index LIMIT ?'
        arguments.append(limit + 1)
        with self.store.read_snapshot():
            rows = list(self.db.execute(query, arguments))
            records = [self._record(context, row, source) for row in rows[:limit]]
        return {'version': 'alignment_site_own_action_page_v1', 'source': source, 'records': records,
                'next_after_decision_index': records[-1]['decision_index'] if len(rows) > limit else None}

    def _record(self, context, row, source_name):
        self._require(row['tool_result'] is not None, 'completed_operation_missing')
        action, actual = json.loads(row['action']), json.loads(row['runtime_result'])
        saved = json.loads(row['tool_result'])
        key = f'{self.run_id}:{context.episode_id}:{row["decision_index"]}'
        expected_id = identity('operation', {'key': key, 'name': action['tool'],
                                            'arguments': action['arguments']})
        self._require(row['operation_key'] == key and row['id'] == expected_id
            and row['name'] == TOOLS[source_name] and actual.get('operation_ref') == expected_id
            and self._equal(json.loads(row['arguments']), action['arguments'])
            and self._equal(json.loads(row['scope']), context.scope), 'operation_identity_conflict')
        self._require(self._equal({k: v for k, v in actual.items() if k != 'pending_work_after_action'}, saved),
                      'operation_outcome_conflict')
        args, result = action['arguments'], saved['result']
        if source_name == 'reference_site_rows':
            alignment, original, binding, artifact, grading = self._reference(args, saved)
        else:
            self._require(self._received_before(context.episode_id, args['observation_ref'],
                row['decision_index']), 'original_hsp_receipt_required')
            from .blast_result_views import _original_hsp
            alignment, original, reference, native = _original_hsp(self.store,
                args['observation_ref'], [args['observation_ref']], plain(context.scope))
            marker = 'native_blast_pairwise' if 'native_blast_pairwise' in alignment else 'native_blast'
            other_marker = 'native_blast' if marker == 'native_blast_pairwise' else 'native_blast_pairwise'
            self._require(saved['record_refs'] == [] and result['observation_ref'] == alignment['id']
                and result['source_ref'] == original['id'] and result['reference_ref'] == reference['id']
                and other_marker not in result
                and self._equal(result.get(marker), alignment[marker]), 'native_hsp_result_conflict')
            binding = self._binding(alignment, original)
            artifact = result.get('site_grading_artifact_ref')
            grading = self._grading(artifact, original) if artifact is not None else None
            if grading is not None and grading.get('sheet') is not None:
                sheet = grading['sheet']
                self._require(sheet.get('schema') == 'blast_hsp_column_sheet_v1'
                    and self._equal(sheet['native_input'], native)
                    and self._equal(sheet['requested_window'], {key: args[key] for key in
                        ('column_offset', 'column_limit')}), 'native_hsp_sheet_conflict')
        if grading is not None and grading.get('sheet') is not None:
            self._sheet_identity(grading['sheet'], alignment, original)
        self._require(grading is None or isinstance(grading, dict), 'grading_envelope_invalid')
        availability = ('legacy_result_ungraded' if grading is None else
                        'grading_unavailable' if grading.get('sheet') is None or grading.get('scores') is None
                        else 'bound')
        normalized = None if grading is None else {key: grading.get(key) for key in ('sheet', 'scores', 'failure')}
        value = {'decision_index': row['decision_index'], 'operation_ref': expected_id,
            'tool_name': action['tool'], 'operation_status': saved['status'], 'arguments': args,
            'binding': binding, 'grading_artifact_ref': artifact, 'grading': normalized,
            'availability': availability, 'feedback_code': (saved.get('feedback') or {}).get('code')}
        canonical(value)
        return value

    def _binding(self, alignment, original, *, result_source=None, result_observation=None):
        descriptor = source_descriptor(self.store, original, alignment)
        return {'alignment_ref': alignment['id'], 'native_source_ref': original['id'],
                'native_artifact_ref': descriptor['native_artifact_ref'],
                'result_source_ref': result_source, 'result_observation_ref': result_observation,
                'native_locator': descriptor['native_locator'] or None}

    def _grading(self, reference, source):
        artifact = self.store.get(reference)
        self._require(artifact.get('record_type') == 'artifact' and artifact.get('media_type') == MEDIA_TYPE,
                      'grading_artifact_required')
        value = json.loads(self.store.get_artifact(reference))
        self._require(set(value) == {'schema', 'provider', 'native_artifact_ref', 'grading'}
            and value['schema'] == SCHEMA and value['provider'] == source['provider']
            and value['native_artifact_ref'] == source['artifact_ref']
            and isinstance(value['grading'], dict), 'grading_custody_conflict')
        canonical(value)
        return value['grading']

    def _reference(self, args, saved):
        result = saved['result']
        alignment = self.store.get(args['alignment_ref'])
        original = self.store.get(alignment['source_ref'])
        source = self.store.get(result['source_ref'])
        observed = self.store.get(result['observation_ref'])
        for record in (alignment, original, source, observed):
            immutable_record(record)
        if original['provider'] in {'biopython.alignment', 'native.phmmer.alignment'}:
            reference_source_operands(self.store, alignment, original)
        self._require(result['complete_result_source_ref'] == source['id']
            and source['id'] in saved['record_refs'] and observed['id'] in saved['record_refs']
            and source['provider'] == 'alignment.sites' and source.get('origin') == 'tool'
            and observed.get('record_type') == 'observation' and observed.get('origin') == 'tool'
            and observed.get('kind') == 'comparison' and observed['source_ref'] == source['id']
            and observed['dependencies'] == [alignment['id']]
            and observed['subject_refs'] == alignment['subject_refs']
            and observed['source_subject_refs'] == alignment['source_subject_refs']
            and source['parent_source_refs'] == [original['id']], 'comparison_custody_conflict')
        positions = (args['positions'] if 'positions' in args else
                     list(range(args['window']['start'], args['window']['end'])))
        body = json.loads(self.store.get_artifact(source['artifact_ref']))
        self._require(body['alignment_ref'] == alignment['id']
            and body['native_provider'] == original['provider']
            and self._equal(body['requested_positions'], positions), 'comparison_selection_conflict')
        candidates = []
        for reference in source.get('auxiliary_artifact_refs', []):
            if self.store.get(reference).get('media_type') == MEDIA_TYPE:
                value = self._grading(reference, source)
                if value.get('sheet') is None or value['sheet'].get('schema') == 'reference_site_comparison_sheet_v1':
                    candidates.append((reference, value))
        self._require(len(candidates) <= 1, 'ambiguous_site_grading')
        artifact, grading = candidates[0] if candidates else (None, None)
        if grading is not None and grading.get('sheet') is not None:
            sheet = grading['sheet']
            selection = ({'kind': 'reference_positions', 'positions': args['positions']}
                if 'positions' in args else {'kind': 'reference_window', **args['window']})
            self._require(self._equal(sheet['selection'], selection)
                and self._equal(sheet['requested_positions'], positions), 'comparison_sheet_selection_conflict')
            if original['provider'] == 'minimap2.mapping':
                from .minimap2_grading_inputs import parse_minimap2_paf_row
                native = sheet['native_input']
                parsed = parse_minimap2_paf_row(paf_row_bytes(
                    self.store, original, alignment['native_minimap2']))
                self._require(self._equal(native['native_row'], parsed),
                    'native_paf_sheet_conflict')
                setup = json.loads(self.store.get_artifact(original['artifact_ref']))
                self._require(sheet['native_parameters']['preset'] == setup['settings']['preset']
                    and sheet['native_parameters']['native_version'] == setup['native_version'],
                    'native_paf_settings_conflict')
                for role, references in (('query', alignment['subject_refs']),
                                         ('reference', alignment['source_subject_refs'])):
                    metadata = native[role + '_metadata']
                    self._require(metadata['subject_ref'] == references[0]
                        and metadata['name'] == references[0]
                        and metadata['length'] == self.store.subject_length(references[0])
                        and metadata['sequence'] == self.sequence_reader(references[0], molecule_model='dna'),
                        'native_paf_operand_conflict')
                quality, encoding = read_quality(self.store, alignment['subject_refs'][0])
                self._require(native['quality'] == quality and native['quality_encoding'] == encoding,
                    'native_paf_quality_conflict')
            else:
                self._require(self._equal(sheet['native_input'], json.loads(
                    self.store.get_artifact(original['artifact_ref']))), 'native_alignment_sheet_conflict')
        return alignment, original, self._binding(alignment, original,
            result_source=source['id'], result_observation=observed['id']), artifact, grading

    def _sheet_identity(self, sheet, alignment, source):
        self._require(self._equal(sheet['source'], source_descriptor(self.store, source, alignment)), 'sheet_source_conflict')
        if source['provider'] == 'ncbi_blast':
            from .blast_search import PROGRAM_UNITS
            request = json.loads(self.store.get_artifact(source['request_ref']))['request']
            alignment_unit = PROGRAM_UNITS[request['algorithm']][2]
            self._require(sheet['program'] == request['algorithm'], 'sheet_processing_model_conflict')
        elif source['provider'] == 'episode.execution_result':
            from .blast_search import PROGRAM_UNITS
            program = alignment['native_blast_pairwise']['program']
            alignment_unit = PROGRAM_UNITS[program][2]
            self._require(sheet['program'] == program, 'sheet_processing_model_conflict')
        elif source['provider'] == 'biopython.alignment':
            native = json.loads(self.store.get_artifact(source['artifact_ref']))
            molecule = biopython_molecule(self.store, source, native)
            alignment_unit = 'aa' if molecule == 'protein' else 'nt'
            self._require(sheet['native_parameters']['molecule'] == molecule, 'sheet_processing_model_conflict')
        else:
            alignment_unit = 'nt' if source['provider'] == 'minimap2.mapping' else 'aa'
        for role, refs in (('query', alignment['subject_refs']), ('reference', alignment['source_subject_refs'])):
            self._require(len(refs) == 1, 'sheet_operand_conflict')
            supplied = sheet['operands'][role]
            expected = operand_descriptor(self.store, refs[0], alignment_unit=alignment_unit)
            if source['provider'] == 'minimap2.mapping':
                # This sheet records the declared DNA processing model. The
                # original material's label remains in its retained record.
                expected.update(unit='nt', molecule='dna')
            self._require(self._equal(supplied, expected), 'sheet_operand_conflict')
        self._require(self._equal(sheet['original_mapping_inputs'], original_mappings(
            self.store, sheet['operands'])), 'sheet_original_mapping_conflict')

    def _received_before(self, episode_id, reference, decision_index):
        current, through, seen = episode_id, None, set()
        while current is not None:
            self._require(current not in seen, 'receipt_lineage_cycle')
            seen.add(current)
            manifest = self.db.execute('SELECT parent_episode_id,through_receipt_index '
                'FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
                (self.run_id, current)).fetchone()
            self._require(manifest is not None, 'receipt_history_unbound')
            row = self.db.execute('SELECT receipt_index,receipt_kind,source_index FROM runtime_record_receipts '
                'WHERE run_id=? AND episode_id=? AND record_ref=?', (self.run_id, current, reference)).fetchone()
            if row is not None and (through is None or row['receipt_index'] <= through):
                if current != episode_id or row['receipt_kind'] == 'initial':
                    return True
                index = row['source_index']
                if type(index) is int and (index <= decision_index if row['receipt_kind'] == 'decision_input'
                                           else index < decision_index):
                    return True
            current, through = manifest['parent_episode_id'], manifest['through_receipt_index']
        return False

    def frozen_facts(self, context, *, sources):
        self._context(context)
        requested = self._requested(context)
        self._require(isinstance(sources, (list, tuple)) and len(sources) == len(set(sources))
            and all(source in TOOLS and source in requested for source in sources), 'requested_source_required')
        if not sources:
            return {}
        columns, parameters = [], []
        for index, source in enumerate(sources):
            columns += [f'json_type(facts,?) AS type_{index}', f'json_extract(facts,?) AS value_{index}']
            parameters += ['$.' + source, '$.' + source]
        row = self.db.execute('SELECT ' + ','.join(columns) + ' FROM runtime_forms '
            'WHERE run_id=? AND episode_id=?', (*parameters, self.run_id, context.episode_id)).fetchone()
        if row is None:
            return None
        result = {}
        for index, source in enumerate(sources):
            if row[f'type_{index}'] is not None:
                self._require(row[f'type_{index}'] == 'array', 'frozen_source_invalid')
                result[source] = json.loads(row[f'value_{index}'])
        canonical(result)
        return result


__all__ = ['AlignmentSiteActionRecords']
