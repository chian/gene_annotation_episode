"""Closed native projections of the gel reader's original numerical outputs."""
from copy import deepcopy as cp

from jsonschema import Draft202012Validator, ValidationError

from ..communication import plain
from gene_annotation_episode.domain import ContractError, canonical
from . import literature_gel_inputs as inputs
from . import literature_gel_calculations as calculations


PROVIDER = 'literature.a105.gel'
OPERATION = 'literature.gel.populate'
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import FACT_SOURCE
VERSION = 'literature_gel_record_v1'
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_display_metadata import FACT_VERSION
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import RAW_COMPONENTS
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import CORRECTED_COMPONENT
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import LANE_COMPONENTS
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import COMPARISON_COMPONENTS
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import COMPONENTS
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import VIEWS
REQUEST_COMPONENTS = 'requested_gel_components'
REQUEST_VIEWS = 'requested_gel_views'
REQUEST_KEYS = 'requested_gel_component_keys'
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_display_metadata import LANE_MEANINGS


from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import obj
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import nullable
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import ref
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import arr
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import enum
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import record_reference
def gel_population_schema():
    return obj({'selection':{'anyOf':[inputs.gel_arguments_schema(),
        inputs.gel_arguments_schema(version=inputs.VERSION_V2)]},
        'comparison':calculations.gel_comparison_schema()})


def validate_population_arguments(arguments):
    value=plain(arguments)
    try:
        Draft202012Validator(gel_population_schema()).validate(value)
        canonical(value)
        selection=inputs.validate_gel_selection(value['selection'])
        comparison=calculations._comparison(value['comparison'], {'selection':selection})
    except (ValueError, TypeError, KeyError, ValidationError) as error:
        raise ContractError('gel_native_arguments_invalid') from error
    return {'selection':selection, 'comparison':comparison}


from gene_annotation_episode.episodic_workflow.root.library.literature_gel_return_contracts import gel_cells_schema
__all__=['PROVIDER','OPERATION','FACT_SOURCE','VERSION','FACT_VERSION','COMPONENTS','VIEWS',
    'RAW_COMPONENTS','CORRECTED_COMPONENT','LANE_COMPONENTS','COMPARISON_COMPONENTS','LANE_MEANINGS',
    'REQUEST_COMPONENTS','REQUEST_VIEWS','REQUEST_KEYS','gel_population_schema','gel_cells_schema','validate_population_arguments']
