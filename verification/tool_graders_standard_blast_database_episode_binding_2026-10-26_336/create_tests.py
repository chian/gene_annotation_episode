"""Adapt accepted custody/return regression cases to the standard contract."""
import ast
from pathlib import Path

root=Path(__file__).resolve().parents[2]
def rename(s):
    s=s.replace('native_blast_database','native_blast_standard_database').replace('native-blast-database','native-blast-standard-database').replace('NativeBLASTDatabase','StandardBLASTDatabase').replace('execution_blast_database_','execution_blast_standard_database_')
    for a,b in [('capture_native_blast_standard_database_bundle','capture_standard_blast_database_bundle'),('validate_native_blast_standard_database','validate_standard_blast_database'),('requested_job_from_native_blast_standard_database','requested_job_from_standard_blast_database'),('native_blast_standard_database_fact_sources','standard_blast_database_fact_sources'),('run_native_blast_standard_database_result_worker','run_standard_blast_database_result_worker')]:s=s.replace(a,b)
    s=s.replace('native_blast_standard_database_result_selector_v1','native_blast_standard_database_selector_v1')
    # Metadata intentionally shares the original wire contract, not job type.
    s=s.replace('native_blast_standard_database_query_metadata_v1','native_blast_database_query_metadata_v1')
    s=s.replace('native_blast_standard_database_sequence_metadata_v1','native_blast_database_sequence_metadata_v1')
    return s
def remove(s,names):
    lines=s.splitlines(keepends=True)
    nodes=[n for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    for node in sorted(nodes,key=lambda n:n.lineno,reverse=True):
        start=min([node.lineno]+[d.lineno for d in node.decorator_list])-1
        del lines[start:node.end_lineno]
    return ''.join(lines)

for kind in ('acquisition','episode_binding','results','returns'):
    source=(root/'tests'/('test_native_blast_database_'+kind+'.py')).read_text()
    if kind=='episode_binding':source=remove(source,{'test_native_convergence_occurrences_cross_the_original_child_boundary'})
    if kind=='returns':source=remove(source,{'test_actual_pre325_generation_and_forwarded_form_replay_without_interpretation','test_new_partial_visibility_does_not_expand_original_empty_received_history'})
    if kind=='results':source=remove(source,{'test_original_metadata_tuple_order_retains_independent_outcomes'})
    s=rename(source).replace("['psiblast', 'deltablast', 'rpsblast', 'rpstblastn', 'blastn_vdb', 'tblastn_vdb']", "['blastn', 'blastp', 'blastx', 'tblastn', 'tblastx']")
    s=s.replace("program='psiblast'","program='blastp'").replace("program='rpsblast'","program='blastp'")
    if kind=='acquisition':
        s=s.replace(', checkpoint_output=False','').replace('run_fixture(path, plan)','run_fixture(path, plan, pbs_jobid=\'313.synthetic\', shadow=manifest[\'module_root\'])')
    if kind=='episode_binding':
        s=s.replace(', checkpoint_output=False','').replace("sequence='ACGT'",'sequence=None')
        s=s.replace("        remote = remote_fixture.__wrapped__(tmp_path, monkeypatch)","        sequence = sequence or ('AC' if query_kind == 'pssm' else 'GCTTGTGGTACC' if program in {'blastx', 'tblastx'} else 'ACGT')\n        remote = remote_fixture.__wrapped__(tmp_path, monkeypatch)")
        s=s.replace("        if query_bytes is not None:", "        if query_kind == 'sequence' and query_bytes is None:\n            query_bytes = ('>one\\n' + sequence + '\\n').encode()\n        if query_bytes is not None:")
        s=s.replace("        if query_kind == 'msa':\n            job['query']['msa_master_record_ordinal'] = 0\n",'')
        s=s.replace("        native_program = program.removesuffix('_vdb')", "        native_program = 'psitblastn' if query_kind == 'pssm' else program")
        s=s.replace("        hsp = native_hsp or hsp", "        if query_kind == 'pssm':\n            hsp.update(query_to=len(sequence), hit_to=3*len(sequence), align_len=len(sequence), identity=len(sequence), qseq=sequence, hseq=sequence, hit_frame=1)\n        else:\n            if program in {'blastx', 'tblastx'}: hsp.update(query_to=12, query_frame=1)\n            if program in {'tblastn', 'tblastx'}: hsp.update(hit_to=12, hit_frame=1)\n        hsp = native_hsp or hsp")
        s=s.replace("program in {'blastn_vdb', 'rpstblastn'}", "program in {'blastn', 'blastx', 'tblastx'}")
        s=s.replace('synthetic-321-','synthetic-336-').replace('test_six_selected','test_five_selected')
        s=s.replace("program='psiblast', version='PSIBLAST 2.17.0+'", "program='blastp', version='BLASTP 2.17.0+'")
        s=s.replace(", 'iteration_convergence': []",'').replace("booleans=['native_converged'] if f == 'iteration_convergence' else []","booleans=[]")
    if kind=='results':
        s=s.replace("consumer='profile', schema_id='unknown.future'", "consumer='query_identity', schema_id='native_blast_database_query_metadata_v1'")
        s=s.replace("'native_blast_metadata_schema_unsupported'", "'native_blast_standard_database_metadata_payload_invalid'")
        s=s.replace("    if program == 'rpstblastn':", "    if program in {'blastx', 'tblastx'}:")
        s=s.replace("    if program == 'tblastn_vdb':", "    if program in {'tblastn', 'tblastx'}:")
        s=s.replace("assert observed['kind'] == ('profile_match' if program in {'rpsblast', 'rpstblastn'} else 'comparison')", "assert observed['kind'] == 'comparison'")
        s=s.replace("assert ('paired_identity' not in values) == (program in {'rpsblast', 'rpstblastn'})", "assert values['paired_identity'] == 1")
        s=s.replace("@pytest.mark.parametrize('kind', ['msa', 'pssm'])", "@pytest.mark.parametrize('kind', ['pssm'])")
        s=s.replace("h = SyntheticHost(tmp_path, monkeypatch, query_kind=kind, query_bytes=query)", "h = SyntheticHost(tmp_path, monkeypatch, program='tblastn', query_kind=kind, query_bytes=query, sequence='ACGT')")
        s=s.replace("options = {'sequence': 'AGGT'}", "options = {'sequence': 'AGGT', 'query_bytes': b'>one\\nACGT\\n'}")
    path=root/'tests'/('test_native_blast_standard_database_'+kind+'.py')
    compile(s,str(path),'exec');path.write_text(s)
print('Created four standard custody, publication, return and episode test modules')
