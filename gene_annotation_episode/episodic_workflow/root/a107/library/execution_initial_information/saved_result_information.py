"""A107 original saved-result reader closure for received initial information.

This host declares no episode, task, action, tool execution or continuation.
Original return/result readers keep their exact class and exception identities.
"""
from copy import deepcopy
import json
from pathlib import Path
from ...communication import plain
from ..received_execution_targets import (
    received_execution_target, retained_expression_nmf_target, is_expression_nmf_selector,
    retained_masking_target, is_masking_selector, retained_utility_target,
    is_utility_selector, selected_result_action)


class SavedResultInformationHost:
    _target = received_execution_target
    _retained_expression_nmf_target = retained_expression_nmf_target
    _expression_nmf_selector = staticmethod(is_expression_nmf_selector)
    _retained_masking_target = retained_masking_target
    _masking_selector = staticmethod(is_masking_selector)
    _retained_utility_target = retained_utility_target
    _utility_selector = staticmethod(is_utility_selector)
    _selected_result_action = selected_result_action

    def __init__(self, factory, *, store, run_id, directory, job_progress_provider):
        definition = plain(factory.as_record())
        self.store, self.run_id, self.directory = store, run_id, Path(directory)
        self.resources = deepcopy(definition['resources'])
        self.job_progress_provider = job_progress_provider
        self.handoff_unit = definition['handoff_unit']
        self.acquired_record_unit = definition['acquired_record_unit']
        from ...native_blast_masking_results import NativeBLASTMaskingResults
        from ...native_blast_masking_returns import NativeBLASTMaskingReturns
        from ...native_blast_utility_results import NativeBLASTUtilityResults
        from ...native_blast_utility_returns import NativeBLASTUtilityReturns
        self.native_blast_masking_results = NativeBLASTMaskingResults(self)
        self.native_blast_masking_returns = NativeBLASTMaskingReturns(self)
        self.native_blast_utility_results = NativeBLASTUtilityResults(self)
        self.native_blast_utility_returns = NativeBLASTUtilityReturns(self)
        self.native_expression_nmf_results = self.native_expression_nmf_returns = None
        if any(configuration.get('native_expression_nmf') for configuration in self.resources.values()):
            from ...native_expression_nmf_results import NativeExpressionNMFResults
            from ...expression_nmf_returns import ExpressionNMFReturns
            self.native_expression_nmf_results = NativeExpressionNMFResults(self)
            self.native_expression_nmf_returns = ExpressionNMFReturns(self)
        self.native_rna_structure_results = self.native_rna_structure_returns = None
        self.rna_structure_comparison_results = self.rna_structure_comparison_returns = None
        if any(configuration.get('native_rna_structure') for configuration in self.resources.values()):
            from ...native_rna_structure_results import NativeRNAStructureResults
            from ...native_rna_structure_returns import NativeRNAStructureReturns
            from ...rna_structure_comparison_results import NativeRNAStructureComparisonResults
            from ...rna_structure_comparison_returns import RNAStructureComparisonReturns
            self.native_rna_structure_results = NativeRNAStructureResults(self)
            self.native_rna_structure_returns = NativeRNAStructureReturns(self)
            self.rna_structure_comparison_results = NativeRNAStructureComparisonResults(self)
            self.rna_structure_comparison_returns = RNAStructureComparisonReturns(self)
