"""Scientific invocation belongs to the actual private literature episode."""
from importlib import import_module
from types import SimpleNamespace

import pytest

from .test_private_literature_bindings import AXIS, HOMES


@pytest.mark.parametrize('home', HOMES)
def test_private_interpretation_and_sheet_owners(home):
    package = AXIS + '.' + home
    binding = import_module(package + '.episode').LiteratureEpisode(
        SimpleNamespace(), rate_population=True, assay_grading_population=True)
    assert binding.execute_reasoning.__module__ == package + '.grading.experimental_interpretation'
    assert binding.reasoning_action_schema.__module__ == package + '.grading.experimental_interpretation'
    assert binding._required_grading_repository.__module__ == package + '.grading.assay_subscoring'
    assert binding._assay_grading_repository.__module__ == package + '.grading.assay_subscoring'
    assert binding._a105_aggregation_repository.__module__ == package + '.scoring.experimental_main_sheet'


@pytest.mark.parametrize('home', HOMES)
def test_private_assessment_implementation_participates_in_binding_identity(home, monkeypatch):
    from pathlib import Path
    package = AXIS + '.' + home
    binding = import_module(package + '.episode').LiteratureEpisode(SimpleNamespace())
    target = Path(import_module(package + '.grading.experimental_interpretation').__file__).resolve()
    before = binding.as_record()
    original = Path.read_bytes
    def altered_bytes(path):
        content = original(path)
        return content + b'\n# changed private implementation fixture\n' if path.resolve() == target else content
    monkeypatch.setattr(Path, 'read_bytes', altered_bytes)
    after = binding.as_record()
    assert before['implementation_sha256'] != after['implementation_sha256']
    assert before['configuration'] == after['configuration']
