"""Focused actual-source boundary for the relocated protein worker."""
import pytest

from .protein_live_owner_checks import CASES, check


@pytest.mark.parametrize('case', CASES)
def test_protein_live_defining_sources(case):
    from ..library import native_protein_structure_worker
    check(case, native_protein_structure_worker)
