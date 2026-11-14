"""Actual original adapter predicates: own roles short-circuit without science."""
from __future__ import annotations
import importlib
from types import SimpleNamespace
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a107'
ADAPTERS = (
    ('local_file_capture_results', 'LocalFileSourceResults'),
    ('native_blast_masking_results', 'NativeBLASTMaskingResults'),
    ('native_blast_utility_results', 'NativeBLASTUtilityResults'),
    ('native_hmmer_results', 'NativeHMMERResults'),
    ('native_blast_results', 'NativeBLASTResults'),
    ('native_blast_database_results', 'NativeBLASTDatabaseResults'),
    ('native_blast_standard_database_results', 'StandardBLASTDatabaseResults'),
    ('native_hmmer_preparation_results', 'NativeHmmerPreparationResults'),
    ('native_expression_nmf_results', 'NativeExpressionNMFResults'),
    ('native_rna_structure_results', 'NativeRNAStructureResults'),
    ('rna_structure_comparison_results', 'NativeRNAStructureComparisonResults'),
    ('native_infernal_results', 'NativeInfernalResults'),
    ('native_infernal_preparation_results', 'NativeInfernalPreparationResults'))

class OriginalSelectedOperandReached(ValueError):
    pass

class Context:
    def __init__(self, role): self.role = role
    @property
    def assignment(self):
        raise OriginalSelectedOperandReached('original_results_operand_reached')


def original_target(context):
    raise OriginalSelectedOperandReached('original_results_operand_reached')


@pytest.mark.parametrize('module_name,class_name', ADAPTERS, ids=[name for name, _ in ADAPTERS])
@pytest.mark.parametrize('role', ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results'))
def test_actual_original_role_predicate_short_circuit_and_selected_operand(module_name, class_name, role):
    module = importlib.import_module(AXIS + '.' + module_name)
    adapter = object.__new__(getattr(module, class_name))
    # Explicit constructor bypass: these ports are only traps proving that no
    # target or assignment is consulted for a non-Results owner context.
    adapter.owner = adapter.binding = SimpleNamespace(_target=original_target)
    context = Context(role)
    if role == 'results':
        with pytest.raises(OriginalSelectedOperandReached, match='^original_results_operand_reached$'):
            adapter.applies(context)
    else:
        assert adapter.applies(context) is False
