"""The yield controller the commissioner names: accumulation, a bounded quality or a finite target. When the
commissioner names none, ``read_from_parent`` made it a finite target of one credit per plan step."""
from yield_control import AccumulationYieldController, BoundedQualityYieldController, CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    kind = parent_input['controller']
    if kind['kind'] == 'accumulation':
        return AccumulationYieldController('library_probe', initial_credit, settings['cost'], settings['parameters'])
    if kind['kind'] == 'bounded':
        return BoundedQualityYieldController('library_probe', initial_credit, settings['cost'], float(kind['maximum']),
                                             settings['parameters'])
    if kind['kind'] == 'completion':
        return CompletionYieldController('library_probe', initial_credit, settings['cost'], float(kind['target']),
                                         settings['parameters'])
    raise ValueError('probe_controller_kind_unknown:' + repr(kind))
