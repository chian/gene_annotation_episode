"""Persist full C2 operands/results, then replay with native parsing and I/O denied.

Run from the repository with .venv/bin/python. The optional output directory
must be new; prior receipts and examples are never replaced.
"""
from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import sys
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import pytest
import test_bvbrc_msa_provider_replay as replay
from gene_annotation_episode import bvbrc_msa_inputs as inputs
from gene_annotation_episode import bvbrc_msa_grader as grader
from gene_annotation_episode import bvbrc_msa_provider_contracts as contracts


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path,value):
    data=(json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()
    with path.open('xb') as handle: handle.write(data)
    return {'path':str(path.relative_to(ROOT)),'sha256':digest(data),'byte_count':len(data)}


def changed_parameters(name,parameters):
    result=deepcopy(parameters)
    if name in ('dna','protein'):
        result['requests'][0]['native_rounding']=None
    elif name=='xmfa':
        result['requests']=[result['requests'][0]]
        result['requests'][0]['case_policy']='preserve'
        result['requests'][0]['selection']['block_columns']=[{'block_index':0,'columns_0based':[0,28,48]}]
    else:
        return None
    return result


def provenance(name):
    if name in ('dna','protein'):
        return 'Retained native MSA frequency/consensus/FASTA output from earlier execution on synthetic sequence inputs; no new native run.'
    if name=='mauve_first_block_projection':
        return 'Explicit synthetic projection of the first block of retained combined.xmfa, with synthetic row labels. No acquired producer .afa or authenticated original input-header relabeling is claimed.'
    if name.startswith('unbound_'):
        return 'Synthetic unsupported source-format claim against retained staged bytes. The unbound extractor requirement and absent source identity survive while literal retained XMFA metrics remain available; this is not a native GenBank/DNAstar execution.'
    if name.startswith('source_') or name in ('xmfa','xmfa_missing_sources'):
        return 'Retained executed XMFA and staged source bytes with explicit synthetic metadata/transport; modifications and original maps are declared fixture evidence, not newly acquired biological records.'
    return 'Synthetic scientific/metadata counterexample using actual native parsers and saved association records; no native alignment/tree execution or external custody is claimed.'


def main():
    out=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parent/'filled_examples_009'
    out.mkdir(exist_ok=False)
    receipt={'cases':[],'complete':False,'new_native_jobs':0,'new_service_calls':0,'new_model_calls':0,
        'scope':'Pure MSA provider; adapter/host/episode integration remains separate.'}
    try:
        for name in replay.CASES:
            op,p=replay.example_operands(name)
            op=json.loads(json.dumps(op)); p=json.loads(json.dumps(p))
            with pytest.MonkeyPatch.context() as guard:
                replay.block_io(guard)
                parsed=inputs.extract_msa_sheet(**op)
                assert parsed['value'] is not None,(name,parsed)
                components=grader.calculate_msa(parsed['value'],p)
                change=changed_parameters(name,p)
                changed=None if change is None else grader.calculate_msa(parsed['value'],change)
            record={'case':name,'provenance':provenance(name),'extract_operands':op,'calculation_parameters':p,'changed_parameters':change}
            answer={'parse_result':parsed,'components':components,'changed_components':changed}
            in_file=write(out/(name+'.inputs.json'),record)
            result_file=write(out/(name+'.answer.json'),answer)
            # Read the disk round trip before denying all runtime I/O.
            loaded=json.loads((out/(name+'.inputs.json')).read_text())
            expected=json.loads((out/(name+'.answer.json')).read_text())
            with pytest.MonkeyPatch.context() as guard:
                replay.block_io(guard)
                fresh=inputs.extract_msa_sheet(**loaded['extract_operands'])
                assert fresh==expected['parse_result'],name
                sheet=expected['parse_result']['value']
                assert grader.calculate_msa(sheet,loaded['calculation_parameters'])==expected['components'],name
                if loaded['changed_parameters'] is not None:
                    assert grader.calculate_msa(sheet,loaded['changed_parameters'])==expected['changed_components'],name
                replay.block_saved_calculations(guard)
                assert contracts.validate_msa_sheet(sheet)==sheet
                assert contracts.validate_msa_components(expected['components'],sheet=sheet)==expected['components']
                if expected['changed_components'] is not None:
                    assert contracts.validate_msa_components(expected['changed_components'],sheet=sheet)==expected['changed_components']
            receipt['cases'].append({'case':name,'inputs':in_file,'answer':result_file,'replay_exact':True,
                'changed_parameters_replay_exact':change is not None,
                'request_kinds':[r['kind'] for r in p['requests']],
                'non_null_results':sum(r['value'] is not None for r in components['results']),
                'requirements':[r['reason_code'] for r in parsed['value']['requirements']]})
        receipt['complete']=True
    except Exception:
        receipt['failure']=traceback.format_exc()
        raise
    finally:
        write(out/'REPLAY_RECEIPT.json',receipt)
    print(json.dumps({'complete':True,'cases':len(receipt['cases']),'changed_parameter_cases':sum(r['changed_parameters_replay_exact'] for r in receipt['cases']),
        'non_null_numerical_results':sum(r['non_null_results'] for r in receipt['cases']),'directory':str(out)},indent=2))


if __name__=='__main__': main()
