"""Caller resource configuration reaches the CLI catalog without starting work."""
import json

import pytest

from gene_annotation_episode.cli import main
from gene_annotation_episode.local_jobs import LocalJobPolicy


def test_cli_records_caller_job_limits_in_catalog(tmp_path, capsys):
    workspace = tmp_path / "state"
    assert main(["init", "--workspace", str(workspace), "--sequence", "ACGT"]) == 0
    capsys.readouterr()
    configuration = tmp_path / "caller.toml"
    configuration.write_text("[local_jobs]\nmemory_bytes = 268435456\nscratch_bytes = 16777216\n")
    assert main(["capabilities", "--workspace", str(workspace), "--config", str(configuration)]) == 0
    catalog = json.loads(capsys.readouterr().out)
    for name in ("sequence.align", "reads.align", "genes.predict", "rna.cmsearch", "reads.map", "source.pdf.info"):
        assert catalog[name]["configuration"]["job_limits"]["memory_bytes"] == 268435456
        assert catalog[name]["configuration"]["job_limits"]["scratch_bytes"] == 16777216
        assert catalog[name]["configuration"]["job_limits"]["wall_seconds"] is None
        assert "job_limits" not in catalog[name]["input_schema"]["properties"]


@pytest.mark.parametrize("config", [
    {"memory_bytes": 0}, {"memory_bytes": True}, {"scratch_bytes": -1},
    {"wall_seconds": 0}, {"memory_byte": 12345},
])
def test_invalid_caller_limits_are_not_silently_replaced(config):
    with pytest.raises((ValueError, TypeError)):
        LocalJobPolicy.from_config(config)


def test_packaged_defaults_match_user_limits_without_a_time_budget():
    policy = LocalJobPolicy.from_config()
    assert policy.memory_bytes == 20 * 1024**3
    assert policy.scratch_bytes == 4 * 1024**3
    assert policy.wall_seconds is None
