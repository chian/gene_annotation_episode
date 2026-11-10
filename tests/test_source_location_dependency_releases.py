"""Current quote retrieval releases and immutable declared-release readback.

Historical receipt cases are explicit synthetic fixtures. They do not relabel
retained production output or claim execution by an archived implementation.
"""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode import literature_kinetic_storage as kinetic
from gene_annotation_episode import literature_kinetic_summary_precision_storage as precision
from gene_annotation_episode import literature_measurement_comparison_storage as comparison
from gene_annotation_episode.domain import ContractError
from test_literature_kinetic_storage import setup as kinetic_setup
from test_literature_kinetic_summary_precision_binding_251 import setup as precision_setup
from test_literature_measurement_comparison_binding_268 import setup as comparison_setup


ORIGINAL_WITNESS_SHA256 = "52069b7d974556631a18d132eaa8bd79b23efc5b7dc2a583b1fff73df4758b6e"


@pytest.mark.parametrize("case", ["kinetic", "precision", "comparison"])
@pytest.mark.parametrize("historical", [False, True], ids=["current", "declared-original"])
def test_dependency_release_allows_population_and_saved_readback(tmp_path, monkeypatch, case, historical):
    if case == "kinetic":
        store, context, arguments = kinetic_setup(
            tmp_path / "state", kind="Km", unit="mM", n=".008", d=".002")
        repository = kinetic.LiteratureKineticRepository(store, context.run_id)
        active_receipt = kinetic._dependencies()
        hashes_field, receipt_field = "sha256", "implementation_dependencies"
    else:
        setup = precision_setup if case == "precision" else comparison_setup
        store, context, arguments, _binding, _source = setup(tmp_path / "state")
        factory = (precision.LiteratureKineticSummaryPrecisionRepository if case == "precision"
                   else comparison.LiteratureMeasurementComparisonRepository)
        repository = factory(store, context.run_id)
        active_receipt = repository._original_implementation()
        hashes_field, receipt_field = "files", "original_implementation"

    with store:
        witness_path = Path(kinetic.__file__).with_name("literature_assay_inputs.py")
        assert active_receipt[hashes_field][witness_path.name] == hashlib.sha256(witness_path.read_bytes()).hexdigest()
        expected_receipt = deepcopy(active_receipt)
        if historical:
            expected_receipt[hashes_field][witness_path.name] = ORIGINAL_WITNESS_SHA256
            if case != "kinetic":
                expected_receipt["version"] = (
                    "summary_precision_original_implementation_v1" if case == "precision"
                    else "measurement_comparison_original_implementation_v2")

        # Only synthetic receipt generation is replaced. Actual readers,
        # calculations, storage and saved-record authentication still execute.
        with monkeypatch.context() as selected_release:
            if historical and case == "kinetic":
                selected_release.setattr(kinetic, "_dependencies", lambda: deepcopy(expected_receipt))
            elif historical:
                selected_release.setattr(repository, "_original_implementation", lambda: deepcopy(expected_receipt))
            outcome = repository.populate(context, arguments, "selected-release")
        assert outcome["status"] == "completed"
        before = list(store.db.iterdump())
        saved = repository.read(outcome["result"]["sheet_ref"])
        assert saved[receipt_field] == expected_receipt
        assert list(store.db.iterdump()) == before
        if case == "kinetic":
            assert saved["cells"]["numerator_parameter"]["value"] == 8
            assert saved["cells"]["denominator_parameter"]["value"] == 2


def test_unknown_kinetic_dependency_release_is_rejected():
    receipt = kinetic._dependencies()
    receipt["sha256"]["literature_assay_inputs.py"] = "0" * 64
    with pytest.raises(ContractError, match="saved_dependency_mismatch"):
        kinetic._validate_dependency_receipt(receipt, kinetic.VERSION)
