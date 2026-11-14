"""Actual NMF tool information and the existing child commissioning route."""
from copy import deepcopy

from .native_expression_nmf_contracts import (NATIVE_EXPRESSION_NMF_REQUESTED_JOB_SCHEMA,
    validate_expression_nmf_bindings)

INSTRUCTIONS = (
    'Factor the supplied gene-by-sample nonnegative expression matrix using scikit-learn NMF. Supply the exact retained '
    'CSV or TSV bytes by absolute input path, byte identity and an explicitly selected comma or tab delimiter. The first '
    'column contains gene labels and the first row sample labels. Original row and column positions identify occurrences; '
    'duplicate labels remain distinct. Optional metadata contains units, positional gene target keys and positional sample '
    'condition/biological-replicate/technical-replicate identifiers with checked original labels. Unsupplied meanings stay '
    'unknown. A public name or candidate annotation is not required. Select positive rank, integer random_state, tolerance, '
    'max_iter and normalization none or column_sum_1000 explicitly. The defaults match rank 10, seed 42, tolerance 0.0001 '
    'and maximum 1000 numerical iterations. Column scaling divides each original sample column by its sum and multiplies '
    'by 1000; a zero denominator is an explicit failure. Preserve negative raw values and reject fitting them. The native '
    'mode fixes random initialization, coordinate descent, Frobenius loss, no regularization and no coordinate shuffling. '
    'Rank may exceed the smaller matrix dimension with random initialization. Numerical iteration count is a solver '
    'parameter. Use the explicitly selected pinned software and local allocation: 20 GiB RAM, 4 GiB scratch, zero swap '
    'and no wall-time cap. Commission through launch and its local-compute child; preparation reserves the selected '
    'pending practical.job.start and the existing host starts the original handle. Poll/collect that same handle. '
    'Input/resource failures and native warnings are returned facts; the responsible episode decides any repair or new '
    'analysis. Native stdout records actual input retention, fit start and fit finish. Monitoring may read selected log '
    'windows/output presence; these are not evidence of productive iterations or scientific credit. '
    'Retain original-input.bin, input.json, prepared.json, complete W and H in factors.json, and fit-manifest.json. '
    'W rows are gene occurrences and columns are fitted components; H rows are components and columns are sample '
    'occurrences. Retain native reconstruction_err_, n_iter_, warnings, selected parameters and actual versions. '
    'The results path loads the exact selected artifacts, populates a numerical sheet, calculates signed residuals, '
    'SSE/Frobenius/RMSE/MAE with their denominators, normalized gene loadings and sample component contributions/fractions. '
    'Reconstruction error is a residual norm. Fitted component fractions describe reconstructed sample abundance and are '
    'not gene-function probabilities. No confidence interval, significance, clinical subtype or annotation score is '
    'inferred. Request only the numerical view and occurrence positions needed by the receiver, with an explicit row '
    'window and any filtering threshold. Full arrays remain retained. Saved-sheet recalculation uses the retained '
    'measurements without fitting or acquiring again; changing rank/preprocessing requires separately selected native work.'
)


def expression_nmf_tool_contracts(bindings, *, resource_kind, resource_id):
    if resource_kind != 'local' or type(resource_id) is not str or not resource_id:
        raise ValueError('nmf_local_resource_required')
    bindings = validate_expression_nmf_bindings(bindings)
    if not bindings:
        return []
    schema = deepcopy(NATIVE_EXPRESSION_NMF_REQUESTED_JOB_SCHEMA)
    schema['properties']['native_expression_nmf']['properties']['software'] = {
        'enum': [deepcopy(row['software']) for row in bindings]}
    return [{'name': bindings[0]['operation'], 'description': 'Fit and retain complete nonnegative expression factors and numerical reconstruction measurements.',
        'resources': 'local', 'instructions': INSTRUCTIONS, 'input_schema': schema,
        'invocation_route': {'kind': 'commission', 'routes': [{'entry_role': 'launch', 'resource_id': resource_id,
            'resource_role': 'launch_local'}]}}]


def expression_nmf_tool_information(bindings, *, resource_kind, resource_id):
    return [{key: row[key] for key in ('name', 'description', 'resources', 'instructions')}
        for row in expression_nmf_tool_contracts(bindings, resource_kind=resource_kind, resource_id=resource_id)]
