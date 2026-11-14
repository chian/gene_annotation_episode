from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
_I32 = 2 ** 31 - 1
_I64 = 2 ** 63 - 1
_PCT = {k: ('number', 0, 100) for k in ('t_low_pct', 't_extend_pct', 't_thres_pct', 't_high_pct')}
PARAMETERS = {('convert2blastmask', 'convert_mask'): {'masking_algorithm': ('text', None, None), 'masking_options': ('text', None, None)}, ('dustmasker', 'mask'): {'window': ('integer', 1, _I32), 'level': ('integer', 0, _I32), 'linker': ('integer', 0, _I32)}, ('segmasker', 'mask'): {'window': ('integer', 1, _I32), 'locut': ('number', 0, None), 'hicut': ('number', 0, None)}, ('windowmasker', 'mask'): {**{k: ('integer', 1, _I32) for k in ('window', 't_thres', 't_low', 't_high', 'set_t_low', 'set_t_high')}, 't_extend': ('integer', 0, _I32), **_PCT, 'dust': ('boolean', None, None), 'dust_level': ('integer', 0, _I32)}, ('windowmasker', 'create_counts'): {'checkdup': ('boolean', None, None), 'mem': ('integer', 1, _I32), 'unit': ('integer', 1, 16), 'genome_size': ('integer', 1, _I64), 'meta': ('text', None, None), 't_low': ('integer', 1, _I32), 't_high': ('integer', 1, _I32), **_PCT}}

def _require(condition, code='invalid_relationship'):
    if not condition:
        raise ContractError('sequence_masking_' + code)

def sequence_masking_operation_schema(*, program: str, mode: str) -> dict:
    """Expose the same closed parameter authority to invocation/tool schemas."""
    _require(type(program) is str and type(mode) is str and ((program, mode) in PARAMETERS), 'unsupported_program_mode')
    parameters = {}
    for name, (kind, low, high) in PARAMETERS[program, mode].items():
        field = {'type': 'string' if program == 'convert2blastmask' else ['string' if kind == 'text' else kind, 'null']}
        if program == 'convert2blastmask' and name == 'masking_algorithm':
            field['minLength'] = 1
            field['allOf'] = [{'pattern': '\\S'}]
        if low is not None:
            field['minimum'] = low
        if high is not None:
            field['maximum'] = high
        if kind == 'text':
            field['pattern'] = '^[^\\u0000]*$'
        parameters[name] = field
    properties = {'version': {'type': 'string', 'const': 'sequence_masking_operation_v1'}, 'program': {'type': 'string', 'const': program}, 'mode': {'type': 'string', 'const': mode}, 'engine_version': {'type': ['string', 'null'], 'minLength': 1, 'pattern': '\\S'}, 'input_format': {'type': 'string', 'const': 'fasta'}, 'output_format': {'type': 'string'}, 'masking_style': {'type': 'string'}, 'parse_seqids': {'type': 'boolean'}, 'requested_parameters': {'type': 'object', 'properties': parameters, 'required': list(parameters), 'additionalProperties': False}}
    if mode == 'convert_mask':
        properties['input_mask_basis'] = {'type': 'string', 'const': 'lowercase_input'}
        properties['molecule'] = {'type': 'string', 'enum': ['dna', 'protein']}
        properties['output_format']['enum'] = ['maskinfo_xml', 'maskinfo_asn1_text', 'maskinfo_asn1_bin', 'interval']
        properties['masking_style']['const'] = 'interval'
        alternatives = None
    elif mode == 'create_counts':
        properties['output_format']['const'] = 'ascii_statistics'
        properties['masking_style']['const'] = 'not_applicable'
        properties['parse_seqids']['const'] = False
        alternatives = None
    else:
        properties['output_format']['enum'] = ['interval', 'fasta']
        properties['masking_style']['enum'] = ['interval', 'soft'] + (['hard'] if program == 'dustmasker' else [])
        alternatives = [{'properties': {'output_format': {'const': 'interval'}, 'masking_style': {'const': 'interval'}}}, {'properties': {'output_format': {'const': 'fasta'}, 'masking_style': {'enum': ['soft', 'hard'] if program == 'dustmasker' else ['soft']}}}]
    result = {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
    if alternatives is not None:
        result['oneOf'] = alternatives
    return result
