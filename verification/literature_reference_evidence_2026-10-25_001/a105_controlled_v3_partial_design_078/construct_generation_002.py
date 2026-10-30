"""Additive correction: preserve generation001, build complete generation002."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'build_declarations_001.py').read_text()
s=s.replace("_001.json'","_002.json'")
s=s.replace("ED['ReadingSelector']=cp(D['ReadingSelector'])", "ED['ReadingSelector']=cp(D['ReadingSelector'])\nED['Authority']=cp(D['Authority'])\nED['ScopeRelation']=cp(D['ScopeRelation'])\nED['RetainedRepresentation']['properties']['reading_key']=null(T)\nED['RetainedRepresentation']['required'].append('reading_key')")
s=s.replace("('projection_status',enum('ready','unresolved_active_reconciliation')),", "('projection_status',enum('ready','unresolved_active_reconciliation')),\n    ('final_projection_basis',null(obj({'reading_assignment':ref('Assignment'),'covariance_scope':enum('base','joint'), 'scope_index':null(I), 'reconciled_roles':arr(enum(*ROLES),uniqueItems=True)}))),")
s=s.replace("'companion_extractions','projection_status','reconciliation_decisions'", "'companion_extractions','projection_status','final_projection_basis','reconciliation_decisions'")
s=s.replace("'source_kinds':arr(enum('primary_source','retained_extraction','synthetic_fixture'),uniqueItems=True)", "'source_kinds':arr(enum('primary_source','retained_extraction','synthetic_fixture'),uniqueItems=True),\n    'original_origins':arr(enum('reported','graph_derived','synthetic'),uniqueItems=True),\n    'measurement_methods':arr(enum('text','graph','not_selected'),uniqueItems=True),\n    **{k+'_state':enum('known','unknown','conflicting') for k in ['endpoint','normalization','subject_construct','condition']}")
s=s.replace("F=obj({'version'", "FD['NumericLocation']={'oneOf':[obj({'kind':{'const':'utf8_span'},'source_ref':T,'start':I,'end':{'type':'integer','minimum':1}}),\n    obj({'kind':{'const':'image_region'},'source_ref':T,'region':ref('Box')}),obj({'kind':{'const':'unresolved'},'source_ref':T})]}\nFD['NativeReading']=obj({k:cp(LD['O_Arm']['properties'][k]) for k in ['value','threshold','relation','approximate','unit','status','origin','digitization_interval','source_observation_id']})\nF=obj({'version'")
s=s.replace("'cell':ref('LocalCell'),'reported_uncertainty':null(ref('UncertaintyCanonical')),", "'cell':ref('LocalCell'),'native_reading':null(ref('NativeReading')),'reported_uncertainty':null(ref('UncertaintyCanonical')),\n    'numeric_locations':arr(ref('NumericLocation')),")
s=s.replace("Constructed seven exact closed schemas", "Constructed seven corrected exact closed schemas")
# Complete generated constructor remains a reviewable standalone source.
with (HERE/'build_declarations_002.py').open('x') as f:f.write(s)
exec(compile(s,str(HERE/'build_declarations_002.py'),'exec'),{'__file__':str(HERE/'build_declarations_002.py'),'__name__':'__main__'})
