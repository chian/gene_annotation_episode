from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'verify_design_004.py').read_text().replace('_004','_006')
s=s.replace("source_covariances=[text['covariance']])", "source_covariances=[{**{k:text['covariance'][k] for k in ['source_ref','artifact_ref','byte_sha256','raw_text','variables','matrix_tokens','exact_matrix','source_model','source_validation','diagnostics']},'document_state':'available'}])")
s=s.replace("projection_state=cov['projection_state']", "document_state=cov['document_state']")
with (HERE/'verify_design_006.py').open('x') as f:f.write(s)
