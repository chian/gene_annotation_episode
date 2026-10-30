"""Scientific display of explicitly available native context observations."""
from collections.abc import Mapping


def is_row(value):
    return (isinstance(value,Mapping) and value.get('bound_kind')=='reported_point_not_operating_domain'
        and 'observation_position' in value and 'context_ref' in value and 'measurement_ref' in value)


def render_rows(parts,rows,records,*,section,table):
    if not rows:return
    records=records or {}
    def meaning(reference):
        if reference is None:return 'unknown'
        record=records.get(reference)
        if not isinstance(record,Mapping):return 'meaning unavailable in the received scientific records'
        return record.get('label',record.get('name','unknown'))
    contexts={r['context_ref']:'Context '+str(i+1) for i,r in enumerate({r['context_ref']:r for r in rows}.values())}
    measurements={r['measurement_ref']:'Measurement '+str(i+1) for i,r in enumerate({r['measurement_ref']:r for r in rows}.values())}
    bases={'source_reported_measurement':'source-reported measurement','source_reported_setting':'source-reported nominal setting',
        'source_supported_inference':'source-supported inference','conditional_assumption':'conditional assumption','unresolved':'unknown','source_value_not_extracted':'source value not extracted by this reader'}
    section(parts,'Native context observations',table(
        ('Context','Source context identity','Biological setting','Requirement','Measurement','Reported point','Unit','Value basis','Basis evidence',
         'SD','SEM','Untyped spread','Reported n','Repetition kind','Sample unit','Cluster','Pairing','Scope match'),
        ((contexts[r['context_ref']],meaning(r['context_ref']),meaning(r['setting_ref']),meaning(r['requirement_ref']),measurements[r['measurement_ref']],
          r['lower'],r['unit'],bases[r['value_basis']],meaning(r['basis_ref']),r['reported_sd'],r['reported_sem'],r['reported_plusminus'],
          r['reported_count'],r['replicate_kind'],meaning(r['sample_unit_ref']),meaning(r['cluster_ref']),r['pairing'],r['scope_match']) for r in rows)))
    section(parts,'Native observation interpretation',
        'Reported points are separate from operating domains and sampling confidence intervals. A nominal culture setting does not establish measured habitat exposure. Reused measurement labels retain a shared source observation; reported repetition counts do not supply an independent context-sampling denominator.')
