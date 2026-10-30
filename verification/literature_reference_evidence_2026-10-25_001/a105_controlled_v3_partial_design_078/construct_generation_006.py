"""Complete shared-stage payload and ordinary native return-array declarations."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'build_declarations_005.py').read_text().replace("_005.json'","_006.json'")
s=s.replace("E['required'].append('covariance_document_scopes')", "E['required'].append('covariance_document_scopes')\nED['BoundCovarianceScope']=obj({'scope':ref('ScopeKey'),'document':null(ref('CovarianceDocument')),\n    'bindings':arr(obj({'reading':ref('ReadingSelector'),'binding':ref('CovarianceBindingExtraction')})),\n    'whole_projection':null(ref('CovarianceExtraction'))})")
s=s.replace("'NATIVE_FACT_SCHEMA_V3_006.json',F)", "'NATIVE_FACT_SCHEMA_V3_006.json',F)\nReturn={'type':'array','items':{k:cp(v) for k,v in F.items() if k not in ('$defs','$schema')},'$defs':cp(FD),\n    '$schema':'https://json-schema.org/draft/2020-12/schema','x-source':'literature_controlled_response_component_cells'}\nput('NATIVE_RETURN_SCHEMA_V3_006.json',Return)")
s=s.replace("'shared_contract':'SHARED_STAGE_EXTENSION_005.md", "'shared_contract':'SHARED_STAGE_EXTENSION_006.md")
with (HERE/'build_declarations_006.py').open('x') as f:f.write(s)
exec(compile(s,str(HERE/'build_declarations_006.py'),'exec'),{'__file__':str(HERE/'build_declarations_006.py'),'__name__':'__main__'})
