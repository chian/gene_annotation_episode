"""Actual relocated source receipt for fresh measurement-validation records.

The original v1 saved-receipt predicate remains in its repository. This owner
describes the distinct current three-file implementation and does not regrade
or reread scientific inputs when checking a saved current receipt.
"""
import hashlib
from pathlib import Path

from gene_annotation_episode.domain import ContractError

VERSION = 'measurement_validation_root_implementation_v2'
_FILES = {
    'literature_measurement_validation_inputs.py': '5ab48a73da231242607593e292fda534664a1be8d21c214e61a39fe09b802d91',
    'library/literature_measurement_validation_calculations.py': '518159debef29515166d4a342df0574a3352651fac5090444afaac5da6acfe27',
    'library/literature_measurement_validation_prompt.py': 'b320f6740c87e7145c97420724af1c203445b693a9b5e818171e0ecd6e4e5317',
}


def prospective():
    """Authenticate the actual current files at the original fresh-read gate."""
    root = Path(__file__).parents[1]
    actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
              for name in _FILES}
    if actual != _FILES:
        raise ContractError('measurement_validation_prospective_dependency_mismatch')
    return {'version': VERSION, 'files': actual}


def retained(receipt):
    """Validate this exact saved current release without reading live sources."""
    if receipt != {'version': VERSION, 'files': _FILES}:
        raise ContractError('measurement_validation_saved_original_receipt_mismatch')
