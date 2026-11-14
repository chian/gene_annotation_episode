"""Check the live protein worker's actual selected defining sources.

No native job or numerical calculation is executed. The first two controls use
the actual running interpreter, dependency versions and selected module bytes.
The historical rejection control installs only fail-if-called observation
sentinels, proving rejection happens before source attribution.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import platform
import sys
from unittest.mock import patch

from .protein_saved_module_identity_checks import current, saved

CASES = ('current_imported_definers', 'legacy_grading_pins_rejected',
         'old_worker_rejected_before_observation')
GRADERS = ('biopython_pairwise_grader', 'alignment_correspondence')


def _source(worker, name):
    spec = importlib.util.find_spec(name)
    assert spec is not None and spec.origin is not None
    return {'module': name, 'sha256': worker._checksum(spec.origin)}


def _current(worker, prefix):
    import numpy
    import Bio
    value = current()
    value.update(python_executable=sys.executable,
                 python_sha256=worker._checksum(sys.executable),
                 python_version=platform.python_version(),
                 numpy_version=numpy.__version__, biopython_version=Bio.__version__)
    value['implementation_files'] += [_source(worker, prefix + name) for name in GRADERS]
    return value


def _rejected(worker, value):
    frozen = deepcopy(value)
    try:
        worker.check_selected_software(value)
    except ValueError as error:
        assert str(error) == 'software_identity_mismatch', str(error)
    else:
        raise AssertionError('unselected defining sources were attributed to the current worker')
    assert value == frozen


def check(case, worker):
    assert case in CASES
    if case == 'current_imported_definers':
        value = _current(worker, 'gene_annotation_episode.episodic_workflow.root.library.')
        assert worker.validate_biopython_correspondence.__module__ == (
            'gene_annotation_episode.episodic_workflow.root.library.biopython_pairwise_grader')
        assert worker.validate_correspondence_artifacts.__module__ == (
            'gene_annotation_episode.episodic_workflow.root.library.alignment_correspondence')
        frozen = deepcopy(value)
        assert worker.check_selected_software(value) is None
        assert value == frozen
    elif case == 'legacy_grading_pins_rejected':
        _rejected(worker, _current(worker, 'gene_annotation_episode.'))
    else:
        value = saved()
        value['implementation_files'] += [
            {'module': 'gene_annotation_episode.' + name, 'sha256': '0' * 64}
            for name in GRADERS]
        # This genuine old descriptor remains accepted by the historical reader.
        assert worker.validate_protein_structure_software(value) == value
        with patch.object(worker, '_checksum', side_effect=AssertionError('unexpected runtime observation')), \
                patch.object(worker.importlib.util, 'find_spec',
                             side_effect=AssertionError('unexpected source resolution')):
            _rejected(worker, value)
