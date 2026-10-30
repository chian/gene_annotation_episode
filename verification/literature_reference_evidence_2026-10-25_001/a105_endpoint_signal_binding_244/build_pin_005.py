"""Data-only repair of retained original legacy fixture closure; no source changes."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3]
OWN=Path(__file__).resolve().parent
PIN=OWN/'pin_005'
assert not PIN.exists()
old=json.loads((OWN/'PIN_004.json').read_text())
base='verification/literature_reference_evidence_2026-10-25_001/primary_f420_partner_013/'
extra={base+name for name in ('PMC8764529.xml','NATIVE_DOCX_TABLES_001.json','NATIVE_BAR_SELECTIONS_001.json','mbio.03501-21-st002.docx','mbio.03501-21-st003.docx','mbio.03501-21-f002.jpg','mbio.03501-21-f006.jpg')}
hashes={}
for relative in set(old['hashes'])|extra:
    if relative in old['hashes']:
        assert hashlib.sha256((OWN/'pin_004'/relative).read_bytes()).hexdigest()==old['hashes'][relative],relative
    source=(ROOT if relative in extra else OWN/'pin_004')/relative
    raw=source.read_bytes();target=PIN/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    hashes[relative]=hashlib.sha256(raw).hexdigest()
(OWN/'PIN_005.json').write_text(json.dumps({'version':'endpoint_signal_joined_pin_v1','base_pin':'PIN_004.json','base_hashes_verified_unchanged':True,'changed_code_paths':[],'additional_retained_fixture_files':sorted(extra),'hashes':dict(sorted(hashes.items())),'reason':'Five existing legacy integration tests initially lacked retained original fixture files in244 pin. No fixture scientific contents changed. Earlier failures preserved.','actual_model_execution':False},indent=2)+'\n')
print(json.dumps({'files':len(hashes),'additional_data_files':len(extra)}))
