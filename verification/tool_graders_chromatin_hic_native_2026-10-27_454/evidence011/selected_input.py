"""Bounded final pinning, corrected independent native dumps and manifest assembly."""
from pathlib import Path
import hashlib
import json
import math
import os
import shlex
import subprocess

ROOT=Path.cwd(); PACKET=ROOT.parent; SETUP=PACKET/'prerequisite007'; BUILD=PACKET/'native009'
def save(path,value): Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def read(path): return json.loads(Path(path).read_text())
def pin(path):
    path=Path(path); data=path.read_bytes()
    return {'path':str(path),'resolved_path':str(path.resolve()),'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}
native=PACKET/'prerequisite003/hictk'
env={**os.environ,'HICTK_NO_TELEMETRY':'1','PATH':str(SETUP/'build-env/bin')+os.pathsep+os.environ['PATH']}
def run(name,args):
    save(ROOT/(name+'.request.json'),{'argv':args,'cwd':str(ROOT),'environment_overrides':{'HICTK_NO_TELEMETRY':'1','PATH':env['PATH']}})
    with (ROOT/(name+'.stdout.txt')).open('wb') as out,(ROOT/(name+'.stderr.txt')).open('wb') as err:
        proc=subprocess.run(args,cwd=ROOT,env=env,stdout=out,stderr=err)
    save(ROOT/(name+'.result.json'),{'returncode':proc.returncode})
    if proc.returncode: raise RuntimeError(f'{name}: exit {proc.returncode}')
run('official_build_metadata',[str(native),'--help-build-meta'])
run('compiler_version',['/usr/bin/g++','--version'])
run('compiler_cc1plus',['/usr/bin/g++','-print-prog-name=cc1plus'])
run('compiler_as',['/usr/bin/g++','-print-prog-name=as'])
run('compiler_ld',['/usr/bin/g++','-print-prog-name=ld'])
run('ninja_dependencies',[str(SETUP/'build-env/bin/ninja'),'-C',str(BUILD/'build'),'-t','deps'])
run('ninja_commands',[str(SETUP/'build-env/bin/ninja'),'-C',str(BUILD/'build'),'-t','commands','writer_harness'])
files={Path('/usr/bin/g++'),Path('/usr/bin/gcc'),Path('/usr/bin/as'),Path('/usr/bin/ld'),SETUP/'build-env/bin/cmake',SETUP/'build-env/bin/ninja',SETUP/'build-env/bin/conan',BUILD/'build/writer_harness',PACKET/'prerequisite002/hictk-pinned-source.tar.gz'}
for line in (ROOT/'ninja_dependencies.stdout.txt').read_text().splitlines():
    if line.startswith('    /') and Path(line.strip()).is_file(): files.add(Path(line.strip()))
for line in (ROOT/'ninja_commands.stdout.txt').read_text().splitlines():
    for item in shlex.split(line):
        if item.startswith('/') and Path(item).is_file(): files.add(Path(item))
cc1plus=Path((ROOT/'compiler_cc1plus.stdout.txt').read_text().strip())
if cc1plus.is_file(): files.add(cc1plus)
save(ROOT/'HARNESS_BUILD_INPUT_PINS.json',[pin(path) for path in sorted(files)])
save(ROOT/'HARNESS_DEPENDENCY_PROVENANCE.json',{'conan_graph':pin(SETUP/'conan-install.stdout.txt'),'pip_report':pin(SETUP/'pip-report.json'),'source_archive':pin(PACKET/'prerequisite002/hictk-pinned-source.tar.gz'),'runtime_pins':read(BUILD/'RUNTIME_PINS.json'),'build_input_pins':str(ROOT/'HARNESS_BUILD_INPUT_PINS.json')})
corrected=[]
for variant in ['valid','nan','zero','negative','inf']:
    path=BUILD/variant/'output.hic'; name='weights_'+variant
    run(name,[str(native),'dump','--resolution','10','--table','weights',str(path)])
    corrected.append({'fixture':pin(path),'request':str(ROOT/(name+'.request.json')),'dump':pin(ROOT/(name+'.stdout.txt')),'returncode':0})
padded=PACKET/'native010/normalization_terminal_padding/output.hic'
run('weights_terminal_padding',[str(native),'dump','--resolution','10','--table','weights',str(padded)])
corrected.append({'fixture':pin(padded),'request':str(ROOT/'weights_terminal_padding.request.json'),'dump':pin(ROOT/'weights_terminal_padding.stdout.txt'),'returncode':0})
save(ROOT/'CORRECTED_WEIGHTS_DUMPS.json',corrected)

raw_expected=read(PACKET/'native004/EXPECTED.json')
variant_expected=read(PACKET/'native005/INDEPENDENT_EXPECTATIONS.json')
weighted_expected=read(BUILD/'INDEPENDENT_EXPECTATIONS.json')
def moment(values):
    n=len(values); total=math.fsum(values); sq=math.fsum(v*v for v in values); mean=total/n
    return {'n':n,'sum':total,'sum_squares':sq,'mean':mean,'population_variance':sq/n-mean*mean}
raw=moment([6,2]); norm=moment([6,0.5]); six=moment([5,1,5,1,5])
assert raw=={'n':2,'sum':8.0,'sum_squares':40.0,'mean':4.0,'population_variance':4.0}
assert norm=={'n':2,'sum':6.5,'sum_squares':36.25,'mean':3.25,'population_variance':7.5625}
assert math.isclose(six['mean'],3.4) and math.isclose(six['population_variance'],3.84)
save(ROOT/'NUMERICAL_CROSSCHECKS.json',{'method':'independent scalar arithmetic over explicitly authored supplied values; no production imports','raw_distance2':raw,'raw_fold':6/raw['mean'],'divisive_distance2':norm,'divisive_fold':6/norm['mean'],'six_windows':six,'six_window_low_z':(1-six['mean'])/math.sqrt(six['population_variance']),'six_window_high_z':(5-six['mean'])/math.sqrt(six['population_variance'])})

software={'official_release_binary':read(PACKET/'prerequisite003/BINARY_PIN.json'),'official_image':read(PACKET/'prerequisite002/SELECTED_IMAGE.json')['descriptor'],'source_commit':'473017312558cd805f470722c2c91a03b91df807','source_archive':pin(PACKET/'prerequisite002/hictk-pinned-source.tar.gz'),'native_version':'hictk-v2.2.0','embedded_build_metadata':pin(ROOT/'official_build_metadata.stdout.txt'),'runtime_dependencies':read(PACKET/'prerequisite003/RUNTIME_DEPENDENCIES.json'),'official_writer_harness_binary':pin(BUILD/'build/writer_harness'),'official_writer_harness_source':pin(BUILD/'writer_harness.cpp'),'official_writer_harness_inputs':pin(ROOT/'HARNESS_BUILD_INPUT_PINS.json'),'independent_spec_writer':pin(PACKET/'native010/fixture_spec_writer.py'),'independent_byte_inspector':pin(PACKET/'native010/byte_inspector.py')}
cases=[]
def add(case_id,path,attempt,kind,inputs,expectations,limitations=None):
    path=Path(path); audit=read(path/'BYTE_AUDIT.json')
    fixture=path/('four.hic' if case_id=='four_bin_raw' else 'output.hic')
    blocks=[]
    for matrix in audit['matrices']:
        for zoom in matrix['zooms']:
            for block in zoom['blocks']:
                blocks.append({'matrix_key':matrix['key'],'resolution_bp':zoom['resolution'],'block_bin_count':zoom['block_bin_count'],'block_column_count':zoom['block_column_count'],**{key:block.get(key) for key in ['block_id','position','compressed_size','compressed_sha256','decoded_sha256','decoded_size','representation','use_float','use_int_x','use_int_y','n_records','decoded_record_count','dense_slots','dense_width','payload_consumed_exactly','zlib_eof']},'filler_slot_count':len(block['filler_slots'])})
    dumps=[pin(p) for p in sorted(path.glob('dump*.stdout.txt'))]
    fixed=[entry for entry in corrected if entry['fixture']['sha256']==pin(fixture)['sha256']]
    cases.append({'case':case_id,'origin':kind,'synthetic_scientific_values':True,'file':pin(fixture),'inputs':[pin(p) for p in inputs],'actual_format':'HIC','actual_version':audit['version'],'actual_chromosomes':audit['chromosomes'],'actual_resolution_list':audit['bp_resolutions'],'matrix_index':audit['master_index_entries'],'observed_encoding':blocks,'normalization_vectors':audit['normalization_vectors'],'native_software_pins_ref':'software','lifecycle_handle':str(PACKET/attempt/'handle.json'),'original_lifecycle_receipt':pin(PACKET/attempt/'receipt.json'),'independent_native_dumps':dumps,'corrected_native_weight_dumps':fixed,'byte_audit':pin(path/'BYTE_AUDIT.json'),'authored_expectations':expectations,'limitations':limitations or []})
add('four_bin_raw',PACKET/'native004','native004','official_hictk_CLI',[PACKET/'native004/four.chrom.sizes',PACKET/'native004/four.coo'],{**raw_expected,'subpopulation_0_30':{'bins':3,'d2_values':[6],'mean':6,'variance':0,'fold':1}},['hictk float32 dense output does not establish other encodings; separate actual files cover them'])
for name in ['six_insulation','terminal_two_chromosomes','terminal_with_all','sparse_multiblock','empty_input']:
    path=PACKET/'native005'/name
    ex=variant_expected.get(name,{})
    if name=='terminal_with_all': ex={**variant_expected['terminal_two_chromosomes'],'chrB_original_index':2,'All_original_index':0,'chrA_original_index':1}
    if name=='empty_input': ex={'matrix_absent':True,'present_zero_block':False,'raw_contacts':None,'implicit_zero_cells':None,'warning':'hictk load empty input omitted the matrix; cannot authorize zeros'}
    add(name,path,'native005','official_hictk_CLI',[path/'input.chrom.sizes',path/'input.coo'],ex)
for variant in ['valid','nan','zero','negative','inf']:
    path=BUILD/variant; ex=weighted_expected if variant=='valid' else {'supplied_vector':read(path/'OUTCOME.json')['vector_values'],'weight_status':read(path/'OUTCOME.json')['scientific_weight_status'],'raw_0_2':6,'selected_normalized_arithmetic':'bin1 masked' if variant=='nan' else 'unavailable for invalid weight','nan_distance2_expected':{'nominal':2,'masked':1,'valid':1,'mean':6,'fold':1} if variant=='nan' else None}
    add('official_divisive_'+variant,path,'native009','official_hictk_API',[PACKET/'native004/four.hic',BUILD/'writer_harness.cpp',path/'writer.request.json'],ex,['Initial weights-table command wrongly supplied --balance and failed; corrected commands are separately retained.','hictk normalized output for invalid weights is serialization evidence, not approved scientific arithmetic.'] if variant not in ['valid','nan'] else ['Initial weights-table command wrongly supplied --balance and failed; corrected commands are separately retained.'])
for outcome in read(PACKET/'native010/ALL_OUTCOMES.json'):
    name=outcome['case']; path=PACKET/'native010'/name
    ex={'expected_rows':outcome['expected_rows']}
    if name.startswith('rowlist_i16_') and name!='rowlist_i16_minus32768' or name.startswith('rowlist_f32_') or name in ['dense_i16_fillers','dense_f32_fillers','normalization_terminal_padding']:
        ex.update(raw_expected)
    if name in ['rowlist_explicit_zero','dense_explicit_zero']:
        ex.update({**raw_expected,'stored_rows':10,'offdiagonal_rows':6,'explicit_zero_rows':1,'implicit_zero_directed_cells':0})
    if name=='present_zero_block': ex.update({'present_matrix_key':'0_0','BP_resolution':10,'block_count':0,'bins':4,'stored_rows':0,'explicit_zero_rows':0,'directed_cells':16,'unordered_cells':10,'implicit_zero_directed_cells':16,'raw_0_2':0,'distance2_mean':0,'fold':None,'qualification':'zero_denominator'})
    if name=='normalization_terminal_padding': ex.update({'native_vector':[1,2,1,2,99],'physical_bin_count':4,'extra_terminal_values':1,'selected_physical_weights':[1,2,1,2],'divisive':weighted_expected})
    add(name,path,'native010','independent_explicit_whole_native_file_serializer',[path/'INPUT.json',PACKET/'native010/fixture_spec_writer.py'],ex,['This file was serialized by the documented packet fixture writer, not produced by hictk or Juicer.','Scientific values are authored synthetic inputs. Official hictk raw dump independently equals all source rows.'])
attempts=[]
for path in sorted(PACKET.iterdir()):
    if path.is_dir() and (path/'receipt.json').is_file():
        receipt=read(path/'receipt.json')
        assert receipt['terminal'] and receipt['quiescent']
        attempts.append({'attempt':path.name,'receipt':pin(path/'receipt.json'),'exit':receipt['returncode'],'terminal':True,'quiescent':True,'source_pins_unchanged':receipt['source_pins_unchanged']})
manifest={'version':'hic_native_fixture_packet_454_v1','scope':'fixed B-L124 native-format prerequisite only; no accounting or production changes','original_authority_attachment':'/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt','original_authority_sha256':'11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7','software':software,'cases':cases,'failed_native_shape_requests':[{'variant':variant,'request':pin(BUILD/variant/'writer.request.json'),'outcome':read(BUILD/variant/'OUTCOME.json'),'stderr':pin(BUILD/variant/'writer.stderr.txt')} for variant in ['short','long']],'attempts':attempts,'final_evidence_lifecycle_handle':str(ROOT/'handle.json'),'final_evidence_receipt_path':str(ROOT/'receipt.json'),'limitations':['No production H1/H2/H3 parser, sheet, calculator, configured episode integration or credit tests are claimed in this packet.','All contact and normalization values are explicitly synthetic scientific data; serialization and independent native decoding are real.','No Juicer int16 writer was installed. Short/mixed-width coverage uses the separately documented full-file native fixture serializer.','No arbitrary corrupt/truncated/checksum/duplicate-index/FRAG/v6-v8 compatibility corpus was manufactured here; those remaining parser failure cases belong to H1/H4 verification.','Source build prerequisite failures and rejected weight shapes remain retained. No hidden native resubmission or resource enlargement occurred.']}
save(PACKET/'FIXTURES.json',manifest)
save(ROOT/'FINAL_INDEX.json',{'fixture_count':len(cases),'manifest':pin(PACKET/'FIXTURES.json'),'original_attempt_count':len(attempts),'numerical_crosschecks':pin(ROOT/'NUMERICAL_CROSSCHECKS.json')})
print(json.dumps({'fixture_count':len(cases),'manifest':pin(PACKET/'FIXTURES.json'),'compile_input_pin_count':len(files),'corrected_weight_dumps':len(corrected)}))
