"""Passive protein receipt fields; never execution configuration."""
from .retained_native_read_profiles import retained_metadata, retained_cgroup
from .protein_structure_contracts import same


def retained_protein_metadata_matches(metadata, *, released):
    if type(metadata) is not dict or type(released) is not bool:
        return False
    try:
        expected = retained_metadata(metadata.get('policy'))
        cgroup = retained_cgroup(metadata.get('policy'))
    except ValueError:
        return False
    enforcement = metadata.get('enforcement')
    if type(enforcement) is not dict:
        return False
    # Unrelated metadata is checked by its handle/receipt owner.
    for key in ('memory', 'swap'):
        if not same(enforcement.get(key), expected['enforcement'][key]):
            return False
    if 'wall_time' in enforcement:
        return False
    actual = metadata.get('verified_cgroup')
    if released:
        if type(actual) is not dict:
            return False
        for key in ('memory_max', 'memory_swap_max'):
            if not same(actual.get(key), cgroup[key]):
                return False
        if 'runtime_max' in actual:
            return False
    return True
