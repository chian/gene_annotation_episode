from pathlib import Path
p=Path('gene_annotation_episode/literature_controlled_response_inputs.py')
s=p.read_text()
s=s.replace('    def __init__(self, arguments, callback):\n','    def __init__(self, arguments, callback):\n        self.unavailable_errors = {}\n',1)
s=s.replace('                loaded = _Unavailable()\n                record.update(state="unavailable"', '                self.unavailable_errors[(reference, representation)] = error\n                loaded = _Unavailable()\n                record.update(state="unavailable"',1)
s=s.replace('            except EOFError:\n                loaded = _Unavailable()', '            except EOFError as error:\n                self.unavailable_errors[(reference, representation)] = error\n                loaded = _Unavailable()',1)
# One unit-aware uncertainty assembly, with a tagged HOST carrier only for v2.
s=s.replace('def _uncertainty(context, selected, response_unit, endpoint, field):\n', 'def _uncertainty(context, selected, response_unit, endpoint, field):\n    tagged = response_unit is not None and "record" in response_unit\n    response_carrier = response_unit\n    response_unit = response_unit["record"] if tagged else response_unit\n')
s=s.replace('            actual_unit = _native_unit(effective_unit["selection"], context.native,\n                effective_unit["selection"]["definition"]["endpoint"] if effective_unit["definition_witnesses"] else None)\n', '            actual_unit = (_native_unit(effective_unit["selection"], context.native,\n                effective_unit["selection"]["definition"]["endpoint"] if effective_unit["definition_witnesses"] else None)\n                if not tagged or relationship == "explicit_unit" else\n                {"canonical_unit": effective_unit["canonical_unit"], "raw_unit": effective_unit["raw_unit"],\n                 "source_defined_unit": None})\n')
start=s.index('    statistic = meanings["statistic"]["effective_value"]',s.index('def _uncertainty('))
s=s[:start]+'''    result = _assemble_uncertainty(selected, meanings=meanings, magnitude=magnitude,
        interval=interval, confidence=confidence, count=count, unit=unit,
        effective_unit=effective_unit, diagnostics=diagnostics, field=field)
    if tagged and result["effective_unit"] is not None:
        result["effective_unit"] = (deepcopy(response_carrier) if relationship == "same_as_response"
            else {"kind": "text", "record": result["effective_unit"]})
    return result


def _assemble_uncertainty(selected, *, meanings, magnitude, interval, confidence,
                          count, unit, effective_unit, diagnostics, field):
    """Arithmetic on retained readings shared by live and detached science."""
'''+s[start:]
# Full original parsing and bindings remain authoritative. Projection differs explicitly.
s=s.replace('def _covariance(context, selected, arms, relationships):','def _covariance(context, selected, arms, relationships, *, owner_profile=False):')
needle='    if result["source_validation"] != "valid":\n        return result\n    states ='
s=s.replace(needle,'    if owner_profile:\n        return _project_owner_covariance(result, matrix, arms, relationships)\n    if result["source_validation"] != "valid":\n        return result\n    states =',1)
# Shared staged facade keeps original validation and call/field order under v1.
a=s.index('    selected = validate_controlled_response_selection(arguments)\n    context = _Context(selected, read_source)',s.index('def read_controlled_response_inputs('))
b=s.index('\n\n_RESULT_FIELDS',a)
s=s[:a]+'''    with open_controlled_response_sources(arguments, read_source=read_source) as context:
        arms = {}
        for role in PRIMITIVE_ORDER:
            nominated = context.arguments["arms"][role]
            if nominated is None:
                arms[role] = None
            else:
                # The legacy ordering (meaning, measurement, context) is retained.
                arms[role] = _arm(context, nominated, "arms." + role)
        return finish_controlled_response_inputs(context, arms=arms)
'''+s[b:]
# Preserve original v1 validator implementation as shared legacy profile branch.
s=s.replace('def validate_controlled_response_extraction(arguments, extraction):','def _validate_v1_saved_science(arguments, extraction):')
# actual four v1 APIs still exposed in __all__ below.
s=s.replace('\n\n__all__ =', '''

def validate_controlled_response_extraction(arguments, extraction):
    return validate_controlled_response_saved_science(arguments, extraction,
        measurement_checks=None)


__all__ =''')
p.write_text(s)
