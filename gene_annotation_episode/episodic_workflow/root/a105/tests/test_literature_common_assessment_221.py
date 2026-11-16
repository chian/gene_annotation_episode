"""Pure common A105 arithmetic with actual218/kinetic native-row custody.

Retained207 source examples are distinguished from synthetic model/covariance
experiments. No common selected-operation, provider/model or credit is run.
"""
import json
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_inputs import COMMON_CONTEXT, COMMON_ARM_CONTEXT, COMMON_ROLES, COMMON_GROUPS, COMMON_ASSUMPTIONS, COMMON_REQUEST, COMMON_POPULATION, COMMON_PARAMETER_KINDS, read_common_assessment_inputs, common_assessment_population_schema, common_assessment_inputs_schema




















def test_pure_operation_factory_retains_only_its_original_two_branches():
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_inputs import compiled_assay_operation_schema
    assert len(compiled_assay_operation_schema()['anyOf']) == 2
    assert COMMON_REQUEST not in json.dumps(compiled_assay_operation_schema())


