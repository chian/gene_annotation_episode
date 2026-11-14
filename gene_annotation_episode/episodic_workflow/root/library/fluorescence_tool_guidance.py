"""Tool-library instructions for the capabilities of configured alternatives.

This is static operation information. Episode TASK/STEERING construction and
the selected numerical job remain outside this module.
"""

_LEGACY_LIMIT = (
    'Performing new compensation or transformations, and importing numerical '
    'reports from other software, remain unavailable in this implementation.'
)
_METHODS = {'fcs_scale_flowio_1_4_0', 'spill_compensate_flowutils_1_2_2'}
_PROFILES = {
    'biomni_facs_log_548_v1': 'the retained FACS population log',
    'biomni_cytokine_log_548_v1': 'the retained cytokine population log',
    'biomni_cytokine_csv_548_v1': 'the retained cytokine frequency CSV',
}


def expand_fluorescence_tool_instructions(base: str, *, bindings: list[dict]) -> str:
    """Expand already-validated, same-operation resource bindings only.

    Capabilities below describe alternatives. The bound invocation schema keeps
    each software/parser/method/profile combination together; this text does not
    create a combined software configuration.
    """
    if not bindings or len({row['operation'] for row in bindings}) != 1:
        raise ValueError('one_fluorescence_operation_required')
    methods, profiles = set(), set()
    for row in bindings:
        if row.get('version') == 'native_fluorescence_binding_v2':
            methods.update(row['preparation_methods'])
            profiles.update(row['report_profiles'])
    if not methods <= _METHODS or not profiles <= _PROFILES.keys():
        raise ValueError('unknown_fluorescence_instruction_capability')
    if not methods and not profiles:
        return base
    if base.count(_LEGACY_LIMIT) != 1:
        raise ValueError('fluorescence_instruction_anchor_mismatch')

    sections = [
        'Preparation and report import are available only in the software '
        'alternatives that explicitly declare them. Keep the selected software, '
        'parser, preparation methods and report profiles in the same configured '
        'alternative. Select each preparation explicitly; provide its recipe '
        'and required input files. A later preparation may use an original '
        'input or an earlier selected preparation. Preserve the original events '
        'and identify the exact measurement domain used by each requested gate '
        'or comparison.'
    ]
    if 'fcs_scale_flowio_1_4_0' in methods:
        sections.append(
            'FCS metadata scaling uses the declared amplification, gain and '
            'time-step metadata through FlowIO 1.4.0. It starts from the '
            'original encoded FCS values and retains those values separately '
            'from the scaled domain. Supply the output channel mapping and '
            'units. A linear native Time channel converted with a supplied '
            'time step can be expressed in seconds; absent time-step metadata '
            'does not establish that conversion. Missing or inconsistent '
            'required metadata produces a qualified unavailable result. Scaling '
            'does not establish fluorescence concentration or a logicle transform.'
        )
    if 'spill_compensate_flowutils_1_2_2' in methods:
        sections.append(
            'Conventional spillover compensation uses FlowUtils 1.2.2 with '
            'the explicitly selected FCS dataset and SPILL or SPILLOVER field. '
            'Provide the exact ordered matrix axes, their input channels and '
            'the matching value-domain basis. Use known uncompensated, '
            'untransformed input. The operation preserves negative values and '
            'original event identities. A missing or singular matrix does not '
            'authorize using raw values as compensated values. Request gates '
            'in the intended output domain; thresholds are not transferred '
            'automatically between domains.'
        )
    if methods:
        sections.append(
            'Only the declared metadata-scaling and conventional-compensation '
            'methods can execute here. Supply other already prepared values '
            'with their actual preparation information when needed.'
        )
    if profiles:
        available = ', '.join(_PROFILES[name] for name in sorted(profiles))
        sections.append(
            'The available report formats are ' + available + '. Select '
            'the exact metric occurrence or CSV position to extract. Retain '
            'the original report and its reported precision. To compare a '
            'reported value with an event-derived value, supply the association '
            'file identifying the same input dataset, samples, domains, gates '
            'and any control pair. Missing association support leaves the '
            'native value available and the comparison unavailable. A report '
            'file alone does not establish successful execution of the software '
            'that originally produced it. Request only the measurements and '
            'qualifications needed by the parent.'
        )
    else:
        sections.append('These configured alternatives do not import native numerical reports.')
    if not methods:
        sections.append('These configured alternatives do not execute new preparation steps.')
    return base.replace(_LEGACY_LIMIT, '\n\n'.join(sections), 1)
