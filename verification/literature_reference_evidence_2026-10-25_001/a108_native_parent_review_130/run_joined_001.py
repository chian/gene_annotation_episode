"""Independent root current-generation typed-boundary composition proof."""
from pathlib import Path
import hashlib
import json
import sys
import pytest
import gene_annotation_episode.literature_episodes as binding
BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_001'
assert Path.cwd().resolve()==PIN
assert Path(binding.__file__).resolve().is_relative_to(PIN)
selection=[
 'tests/test_literature_context_native_integration.py',
 'tests/test_literature_context_native_observations.py::test_same_physical_number_survives_recipe_and_excerpt_changes',
 'tests/test_literature_context_native_observations.py::test_distinct_source_contexts_can_share_one_reported_setting',
 'tests/test_literature_context_native_observations.py::test_not_extracted_basis_cannot_carry_an_extracted_numeric_value',
 'tests/test_literature_context_meanings_integration.py',
 'tests/test_literature_reaction_meanings_integration.py',
 'tests/test_literature_perturbation_covariance_meanings.py::test_ordinary_child_parent_and_first_read_only_reconstruction_keep_actual_covariance_meaning',
]
args=['-q','-x','--junitxml='+str(BASE/'TESTS_001.xml'),*selection]
(BASE/'COMMAND_001.json').write_text(json.dumps({'cwd':str(PIN),'python':sys.executable,'args':args,'scope':'Constructed sources; no primary paper acquisition or configured-model scientific execution.'},indent=2)+'\n')
result=pytest.main(args)
imports={}
for name,module in tuple(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if not file or not name.startswith(('gene_annotation_episode','method_loop','test_literature')):continue
 p=Path(file).resolve()
 if p.suffix!='.py':continue
 assert p.is_relative_to(PIN),(name,str(p))
 imports[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(BASE/'IMPORTS_001.json').write_text(json.dumps(imports,indent=2)+'\n')
manifest=json.loads((BASE/'PIN_MANIFEST_001.json').read_text())['files']
changed=[name for name,digest in manifest.items() if hashlib.sha256((PIN/name).read_bytes()).hexdigest()!=digest]
(BASE/'RESULT_001.json').write_text(json.dumps({'exit_code':int(result),'checked_snapshot_files':len(manifest),'changed_files':changed,'checked_imports':len(imports),'limits':'Ordinary scripted typed delivery and first source-free read-only reconstruction; no new live-model or independent-worker claim.'},indent=2)+'\n')
assert not changed,changed
raise SystemExit(int(result))
