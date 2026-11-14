"""Original successful producer bundles are replayed, never reexecuted."""
import json
from pathlib import Path
import pytest
from gene_annotation_episode.episodic_workflow.root.a101.native_blast_driver import run_native_blast,validate_native_blast_bundle_files
from blast_pairwise_fixture import original_bundle, replay_copy

ROOT=Path(__file__).resolve().parents[5]/'gene_annotation_episode/episodic_workflow/root/a101/tests/fixtures/blast_pairwise'
PLANS=sorted(ROOT.glob('native_examples/*/plan.json'))+sorted(ROOT.glob('native_ranges/*/plan.json'))


@pytest.mark.parametrize('path',PLANS,ids=lambda p:p.parent.name)
def test_all_twenty_actual_native_bundles_keep_complete_custody_and_replay(path,monkeypatch,tmp_path):
    def forbidden(*a,**k):pytest.fail('immutable native replay invoked process')
    monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.a101.native_blast_driver.subprocess.run',forbidden)
    saved_plan=json.loads(path.read_bytes())
    plan,bundle,saved_bundle,root=replay_copy(path,tmp_path)
    original=(path.parent/'attempt/bundle.json').read_bytes()
    assert json.loads(original)==saved_bundle
    assert bundle['returncode']==0 and bundle['failures']==[]
    assert len(bundle['artifacts'])==3
    assert len(bundle['inputs'])==2
    assert validate_native_blast_bundle_files(bundle,root)==bundle
    assert run_native_blast(plan)==bundle
    assert original_bundle(json.loads((root/'bundle.json').read_bytes()),
        saved_plan=saved_plan,new_attempt=root)==saved_bundle
    assert '-subject' in bundle['realized_argv'] and '-db' not in bundle['realized_argv']
    assert plan['policy']=={'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
