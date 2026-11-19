"""Continuation: accumulation of the signed measured credit, with the cost and parameters the commission binds.

The old estimator was the accumulation controller with the commission's ``yield_bindings['hpc_prediction']``
cutoff (now the controller's cost) and parameters. Its own forecast packet for a prediction that is ready
without new measured improvement is not carried: only this controller stops the Episode."""
from yield_control import AccumulationYieldController, YieldParameters

ROLE = 'hpc_prediction'


def yield_controller(initial_credit, settings, parent_input):
    identity = parent_input['commission_identity']
    if 'commission_id' not in identity:
        raise NotImplementedError('hpc_commission_source_ref_yield_binding_not_in_parent_input: the commission '
                                  'named by commission_source_ref is a record; the controller is built from '
                                  'settings and the parent input only')
    commission = settings['commissions'][identity['commission_id']]
    if 'yield_bindings' not in commission:
        raise ValueError('hpc_commission_yield_binding_required:' + ROLE)
    chosen = commission['yield_bindings'][ROLE]
    return AccumulationYieldController('hpc_resource_prediction', initial_credit, chosen['cutoff'],
                                       YieldParameters(**chosen['parameters']))
