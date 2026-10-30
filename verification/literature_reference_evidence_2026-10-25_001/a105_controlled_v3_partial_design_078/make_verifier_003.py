from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'verify_design_002.py').read_text().replace('_002','_003')
s=s.replace("source_variable_indices=[ia,ib] if covariance else [],model_readings=[],unresolved_readings=[])", "source_variable_indices=[ia,ib] if covariance else [],model_readings=[],unresolved_readings=[],\n numeric_fields=[dict(reading=r,fields=['unit','status','relation','approximate','origin','digitization_interval_presence'] if covariance else ['value','threshold','relation','approximate','unit','status','origin','digitization_interval']) for r in selectors],\n full_source_covariance_required=covariance)")
s=s.replace("covariance_owner_ids=[],source_variable_indices=[],model_readings=[],unresolved_readings=[])))", "covariance_owner_ids=[],source_variable_indices=[],model_readings=[],unresolved_readings=[],\n    numeric_fields=[dict(reading=rs,fields=['value','threshold','relation','approximate','unit','status','origin','digitization_interval'])],full_source_covariance_required=False)))")
with (HERE/'verify_design_003.py').open('x') as f:f.write(s)
