"""Native provider affinity stays inside the owned workflow's CPU allowance."""
import json
import os
import subprocess
import sys

import pytest

from gene_annotation_episode.providers import ModelCallError, _model_process_command


def test_native_provider_child_sees_one_cpu_without_changing_parent_affinity():
    from gene_annotation_episode.workflow_budget import active_budget
    bounds = active_budget()["environment_bounds"]
    before = os.sched_getaffinity(0)
    command, selected = _model_process_command([sys.executable, "-B", "-c",
        "import json, os; print(json.dumps(sorted(os.sched_getaffinity(0))))"], bounds)
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == sorted(selected)
    assert len(selected) == 1 and set(selected) <= before
    assert os.sched_getaffinity(0) == before


def test_provider_affinity_preserves_the_requested_model_command(monkeypatch):
    monkeypatch.setattr(os, "sched_getaffinity", lambda _: {4, 7, 9})
    monkeypatch.setattr("gene_annotation_episode.providers.shutil.which", lambda _: "/usr/bin/taskset")
    original = ["codex", "-c", 'model="configured-model"', "app-server", "--stdio"]
    command, selected = _model_process_command(original, {"cpu_percent": 100})
    assert command[-len(original):] == original
    assert len(selected) == 1 and selected[0] in {4, 7, 9}


def test_missing_affinity_tool_does_not_fall_back_to_all_host_cpus(monkeypatch):
    monkeypatch.setattr("gene_annotation_episode.providers.shutil.which", lambda _: None)
    with pytest.raises(ModelCallError, match="model_cpu_affinity_tool_unavailable"):
        _model_process_command(["codex", "app-server"], {"cpu_percent": 100})
