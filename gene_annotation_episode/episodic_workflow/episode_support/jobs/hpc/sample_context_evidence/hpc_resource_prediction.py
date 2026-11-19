"""Private finite measured-resource values for A108 execution receipts."""
import math

RESOURCE_UNITS = {'cpu_seconds': 'cpu_seconds', 'memory_bytes': 'bytes'}

def measured_value(metric, item):
    if metric in RESOURCE_UNITS:
        if item.get('unit') != RESOURCE_UNITS[metric]:
            raise ValueError('resource_measurement_unit_conflict:'+metric)
        value = item['value']
    else:
        value = item['seconds']
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('nonnegative_finite_measured_value_required')
    return value

