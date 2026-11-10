"""Original successful producer bundles are replayed, never reexecuted."""
import json
from pathlib import Path
import pytest
from gene_annotation_episode.native_blast_driver import run_native_blast,validate_native_blast_bundle_files

ROOT=Path(__file__).resolve().parents[1]/'verification/tool_graders_blast_pairwise_2026-10-26_294'
PLANS=sorted(ROOT.glob('native_examples/*/plan.json'))+sorted(ROOT.glob('native_ranges/*/plan.json'))


@pytest.mark.parametrize('path',PLANS,ids=lambda p:p.parent.name)
def test_all_twenty_actual_native_bundles_keep_complete_custody_and_replay(path,monkeypatch):
    def forbidden(*a,**k):pytest.fail('immutable native replay invoked process')
    monkeypatch.setattr('gene_annotation_episode.native_blast_driver.subprocess.run',forbidden)
    plan=json.loads(path.read_bytes());root=Path(plan['attempt_directory'])
    original=(root/'bundle.json').read_bytes();bundle=json.loads(original)
    assert bundle['returncode']==0 and bundle['failures']==[]
    assert len(bundle['artifacts'])==3
    assert len(bundle['inputs'])==2
    assert validate_native_blast_bundle_files(bundle,root)==bundle
    assert run_native_blast(plan)==bundle
    assert (root/'bundle.json').read_bytes()==original
    assert '-subject' in bundle['realized_argv'] and '-db' not in bundle['realized_argv']
    assert plan['policy']=={'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
