"""Current real binding descriptors consume two packaged reader schema assets."""
import hashlib
from importlib import import_module
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
AXIS=__package__.rsplit('.tests',1)[0]
HOMES=sorted(p.parent.relative_to(ROOT).as_posix() for p in ROOT.rglob('binding_record.py') if 'tests' not in p.relative_to(ROOT).parts)
ASSETS=('library/retained_input_authority/bvbrc_appservice_schemas.json','library/retained_input_authority/literature_assay_grading_legacy_cells_v1.json')

def test_declared_runtime_assets_match_actual_loader_bytes():
    values=import_module(AXIS+'.runtime_assets').required_runtime_asset_fingerprints()
    assert set(values)=={'library/retained_input_authority/bvbrc_appservice_schemas.json','library/retained_input_authority/literature_assay_grading_legacy_cells_v1.json'}
    assert values=={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in values}

@pytest.mark.parametrize('home',HOMES)
def test_actual_binding_fingerprint_consumes_each_schema_without_changing_configuration(tmp_path,monkeypatch,home):
    episode=import_module(AXIS+'.'+home.replace('/','.')+'.episode')
    if home=='scientific_process':
        library=import_module(AXIS+'.scientific_process_library').ScientificProcessLibrary(ROOT/'tests/fixtures/retained_protein_reader_336/run/scientific-process-library')
        tools=import_module(AXIS+'.scientific_tool_library').ScientificToolLibrary.freeze(tmp_path/'tools',catalog=[],tool_info=True)
        binding=episode.ScientificProcessEpisode(object(),library=library,tool_library=tools,child_roles=('scientific_process',))
    else:binding=episode.LiteratureEpisode(object())
    before=binding.as_record();read=Path.read_bytes
    for asset in ASSETS:
        selected=(ROOT/asset).resolve();reads=[]
        def controlled(path):
            raw=read(path)
            if path.resolve()==selected:reads.append(path);return raw+b' '
            return raw
        with monkeypatch.context() as patch:
            patch.setattr(Path,'read_bytes',controlled)
            after=binding.as_record()
        assert reads and before['implementation_sha256']!=after['implementation_sha256']
        assert {k:v for k,v in before.items() if k!='implementation_sha256'}=={k:v for k,v in after.items() if k!='implementation_sha256'}
    assert binding.as_record()==before
