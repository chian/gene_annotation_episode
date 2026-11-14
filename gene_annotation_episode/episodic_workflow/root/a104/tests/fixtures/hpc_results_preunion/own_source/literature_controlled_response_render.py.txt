"""Render possessed controlled-response cells without expanding private numbers."""
from collections.abc import Mapping

from .communication import plain
from .domain import canonical
from .literature_binding_interaction_render import overlaps_numbers

FACT_VERSION = 'literature_controlled_response_component_fact_v3'


def is_row(row):
    return isinstance(row, Mapping) and row.get('version') == FACT_VERSION


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for rows in report.values():
                if isinstance(rows, (tuple, list)):
                    yield from (row for row in rows if is_row(row))


def _locations(rows):
    return [location for row in rows for location in row['numeric_locations']]


def _binding_refs(rows, bindings):
    for row in rows:
        yield from (item['record_ref'] for item in (bindings or {}).get(row['sheet_ref'], {}).values())


def hidden_records(reports, records, *, bindings=None):
    rows = list(rows_from_reports(reports))
    locations = _locations(rows)
    # Hiding applies to automatic context expansion. A separately selected,
    # nonoverlapping source fact retains its ordinary display.
    return {row['sheet_ref'] for row in rows} | set(_binding_refs(rows, bindings)) | {
        ref for ref, record in records.items() if overlaps_numbers(record, locations)}


def render_received(parts, rows, records, *, section, table, values, bindings=None):
    rows = list(rows)
    if not rows:
        return
    locations = _locations(rows)
    def label(row, cid):
        binding = (bindings or {}).get(row['sheet_ref'], {}).get(cid)
        record = records.get(binding['record_ref']) if binding else None
        location=binding['canonical_witness_location'] if binding else None
        if location and location['kind']=='image':
            location={'kind':'image_region','source_ref':location['original_source_ref'],'region':location['region']}
        if record is None or overlaps_numbers(record, locations, location):
            return 'source-bound meaning retained for scoped access'
        return record.get('label', 'source-bound meaning retained for scoped access')
    scopes=[]
    def display_scope(row):
        scope=row['joint_scope_context']
        if scope is None:return None
        token=canonical(plain(scope))
        for ordinal,(seen,_) in enumerate(scopes,1):
            if token==seen:return ordinal
        scopes.append((token,row));return len(scopes)
    ordinals=[display_scope(row) for row in rows]
    # Presentation ordinals are local to these possessed rows. Original scope
    # indices, exact keys, free reading tokens and source IDs stay internal.
    section(parts, 'Requested controlled response components', table(
        ('View', 'Component', 'Source scope', 'Value', 'Lower', 'Upper', 'Unit', 'Status', 'Origin', 'Qualifications', 'Unavailable reasons'),
        ((r['kind'], r['component'], ordinal,
          r['cell'].get('value'), r['cell'].get('lower'), r['cell'].get('upper'), r['cell']['unit'],
          r['cell']['status'], r['cell']['origin'], r['cell']['conditional_on'], r['cell']['unavailable_reason']) for r,ordinal in zip(rows,ordinals))))
    for ordinal,(_,row) in enumerate(scopes,1):
        scope=row['joint_scope_context']
        def witnesses(relation):
            return '; '.join('source witness unavailable' if w['authentication']=='unavailable'
                else label(row,w['witness_ref']) for w in relation['witnesses']) or 'no selected witness'
        relationships=[('assignment applicability',scope['assignment_admissibility'])]+[
            (name.replace('_',' '),scope[name]) for name in ('normalization','calibration','revision','covariance_scope','model_scope')]
        section(parts,'Source scope '+str(ordinal)+' relationships',table(
            ('Relationship','Selected meaning','Retained effective meaning','Source witness'),
            ((name,r['selected_value'],r['effective_value'],witnesses(r)) for name,r in relationships)))
        section(parts,'Source scope '+str(ordinal)+' applicability',values(scope['effective_admissibility']))
        section(parts,'Source scope '+str(ordinal)+' reading arrangement',table(('Experimental role','Source representation'),
            ((role.replace('_',' '),'originally nominated reading' if key is None else 'companion source reading')
                for role,key in scope['reading_assignment'].items())))
        section(parts,'Source model requests',table(('Meaning','Selected meaning','Retained effective meaning','Source witness'),
            ((name.replace('_',' '),r['selected_value'],r['effective_value'],witnesses(r)) for name,r in scope['requested_model'].items())))
        section(parts,'Effective scoped source model',values({k:scope['effective_model'][k] for k in ('variance_status','model_kind')}))
        diagnostics=scope['effective_model']['diagnostics']
        if diagnostics:section(parts,'Scoped source model qualifications',table(('Qualification','Meaning'),
            ((d['code'].replace('_',' '),d['domain'].replace('_',' ')) for d in diagnostics)))
        covariance=scope['covariance_context']
        section(parts,'Scoped source covariance',values(None if covariance is None else {k:covariance[k]
            for k in ('source_validation','projection_state','source_model')}))
    for row in rows:
        context = row['context']
        section(parts, row['kind'].replace('_',' ')+' '+row['component'].replace('_',' ')+' meaning', table(
            ('Meaning', 'State', 'Source interpretation'), [
                ('endpoint', context['endpoint_state'], label(row, context['endpoint_id']) if context['endpoint_id'] else 'unknown'),
                ('normalization', context['normalization_state'], label(row, context['normalization_id']) if context['normalization_id'] else 'unknown'),
                ('subject or construct', context['subject_construct_state'], '; '.join(label(row,cid) for cid in context['subject_construct_ids']) or 'unknown'),
                ('condition', context['condition_state'], '; '.join(label(row,cid) for cid in context['condition_ids']) or 'unknown'),
                ('physical observation', context['owner_state'], '; '.join(label(row,cid) for cid in context['owner_ids']) or 'unknown')]))
        section(parts, 'Controlled response qualifications', values({k: context[k] for k in (
            'condition_control_applications','control_reuse','protein_arrangements','variance_status','model_kind',
            'representation_state','source_kinds','original_origins','measurement_methods')}))
        if row['native_reading'] is not None:
            section(parts, 'Requested native reading', values({k:v for k,v in row['native_reading'].items()
                if k!='source_observation_id'}))
            # This uncertainty belongs only to the selected native reading.
            section(parts, 'Requested source uncertainty', values({
                'magnitude_and_interval_unit':row['reported_uncertainty_unit'] or 'unknown',
                **row['reported_uncertainty']}))


def render_own_result(parts, content, *, section, table, values, records=None, bindings=None):
    if not isinstance(content, Mapping):
        return False
    if 'result' in content and isinstance(content['result'], Mapping):
        content = content['result']
    cells = content.get('cells')
    if not isinstance(cells, (tuple,list)) or not all(is_row(row) for row in cells):
        return False
    if not cells and 'component_keys' not in content:
        return False
    render_received(parts,cells,records or {},section=section,table=table,values=values,bindings=bindings)
    return True


__all__=['is_row','rows_from_reports','hidden_records','render_received','render_own_result']
