"""Bounded display of received parent-depletion cells; no private sheet reads."""
from collections.abc import Mapping

def is_row(value):
    return (isinstance(value,Mapping) and value.get('evaluation_scope')=='finite_parent_compound_removal'
        and isinstance(value.get('component'),str) and isinstance(value.get('sheet_ref'),str))

def render_received(parts,rows,*,section,table):
    if not rows:return
    first=rows[0]
    section(parts,'Finite parent-removal experiment',table(('Meaning','Source-reported scope'),[
        ('Analyte',first['compound']),('Submixture',first['submix']),
        ('Time (h)',first['time_hours']),('Readout','relative parent-compound disappearance'),
        ('Raw normalization denominator',first['normalization_status']),
        ('Replicate unit',first['repetition_basis']),
        ('Active-control covariance',first['active_control_covariance']),
        ('Mutant protein amount equality',first['equal_mutant_protein_amount']),
        ('Studied-enzyme product identity',first['product_identity_for_studied_enzyme'])]))
    section(parts,'Requested parent-removal numerical components',table(
        ('Component','Value','Unit','Origin','Workbook cell(s)'),[
            (r['component'],r['value'],r['unit'],r['origin'],', '.join(r['source_cell_addresses'])) for r in rows]))
    if any(r['component'].startswith('active_minus_') for r in rows):
        section(parts,'Dependence and uncertainty',
            'Both active-control differences reuse the same active measurement. Per-arm SD does not supply a difference SD, SE, confidence interval or independent replication count. The differences describe parent disappearance; product coupling and annotation credit remain unknown.')

__all__=['is_row','render_received']
