"""Actual descriptor operands; byte perturbations are read interception, not edits."""
from importlib import import_module
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY=ROOT.parents[3]
AXIS=__package__.rsplit('.tests',1)[0]
HOMES=sorted(p.parent.relative_to(ROOT).as_posix() for p in ROOT.rglob('binding_record.py') if 'tests' not in p.relative_to(ROOT).parts)
EXTERNAL=('gene_annotation_episode/__init__.py','gene_annotation_episode/episodic_workflow/__init__.py',
          'gene_annotation_episode/episodic_workflow/root/__init__.py','gene_annotation_episode/episodic_workflow/root/receiving_context.py')

@pytest.mark.parametrize('home',['independent',*HOMES])
def test_actual_descriptor_reads_all_four_defining_sources_without_changing_configuration(tmp_path,monkeypatch,home):
    if home=='independent':
        descriptor=import_module(AXIS+'.independent_execution').implementation_sha256
        def capture():return {'implementation_sha256':descriptor()}
    else:
        episode=import_module(AXIS+'.'+home.replace('/','.')+'.episode')
        if home=='scientific_process':
            library=import_module(AXIS+'.scientific_process_library').ScientificProcessLibrary(ROOT/'tests/fixtures/retained_protein_reader_336/run/scientific-process-library')
            tools=import_module(AXIS+'.scientific_tool_library').ScientificToolLibrary.freeze(tmp_path/'tools',catalog=[],tool_info=True)
            binding=episode.ScientificProcessEpisode(object(),library=library,tool_library=tools,child_roles=('scientific_process',))
        else:binding=episode.LiteratureEpisode(object())
        capture=binding.as_record
    before=capture();read=Path.read_bytes
    for source in EXTERNAL:
        selected=(REPOSITORY/source).resolve();reads=[]
        def controlled(path):
            raw=read(path)
            if path.resolve()==selected:reads.append(path);return raw+b'\n# controlled descriptor operand only\n'
            return raw
        with monkeypatch.context() as patch:
            patch.setattr(Path,'read_bytes',controlled)
            after=capture()
        assert reads and before['implementation_sha256']!=after['implementation_sha256']
        assert {k:v for k,v in before.items() if k!='implementation_sha256'}=={k:v for k,v in after.items() if k!='implementation_sha256'}
    assert capture()==before
