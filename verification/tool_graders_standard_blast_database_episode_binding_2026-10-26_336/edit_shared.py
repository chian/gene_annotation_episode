"""One-time additive standard branch installation, with original source custody."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
package = root / 'gene_annotation_episode'
evidence = Path(__file__).parent
names = 'practical_execution_records practical_execution_operations practical_pbs_operations execution_progress execution_episodes communication domain state evidence_geometry evidence_axis_contracts alignment_site_native blast_result_views infernal_result_presentation'.split()
before = evidence / 'shared_before'
before.mkdir(exist_ok=False)
for name in names:
    (before / (name + '.py')).write_bytes((package / (name + '.py')).read_bytes())
(evidence / 'SHARED_BEFORE_001.json').write_text(json.dumps([dict(path=str((package / (n+'.py')).relative_to(root)), sha256=hashlib.sha256((package / (n+'.py')).read_bytes()).hexdigest()) for n in names], indent=2)+'\n')

def standard(value):
    value = value.replace('NATIVE_BLAST_DATABASE', 'NATIVE_BLAST_STANDARD_DATABASE').replace('NativeBLASTDatabase', 'StandardBLASTDatabase').replace('native_blast_database', 'native_blast_standard_database').replace('native-blast-database', 'native-blast-standard-database').replace('execution_blast_database_', 'execution_blast_standard_database_')
    for a,b in [('validate_native_blast_standard_database','validate_standard_blast_database'),('native_blast_standard_database_tool_contracts','standard_blast_database_tool_contracts'),('native_blast_standard_database_fact_sources','standard_blast_database_fact_sources'),('native_blast_standard_database_metric_definitions','standard_blast_database_metric_definitions'),('is_native_blast_standard_database_target','is_standard_blast_database_target'),('prepare_native_blast_standard_database_inputs','prepare_standard_blast_database_inputs'),('populate_native_blast_standard_database_sheets','populate_standard_blast_database_sheets'),('calculate_native_blast_standard_database_sheets','calculate_standard_blast_database_sheets'),('validate_standard_blast_database_result_selector','validate_standard_blast_database_selector'),('validate_native_job_inputs','validate_standard_blast_job_inputs'),('validate_selected_inputs','validate_standard_blast_selected_inputs')]:
        value = value.replace(a,b)
    return value

def block(text, needle):
    start = text.index(needle)
    start = text.rfind('\n',0,start)+1
    lines=text[start:].splitlines(keepends=True)
    indent=len(lines[0])-len(lines[0].lstrip())
    end=start+len(lines[0])
    for line in lines[1:]:
        if line.strip() and len(line)-len(line.lstrip()) <= indent:
            break
        end+=len(line)
    return start,end,text[start:end]

def duplicate(text, needle, *, transform=standard, chain=False):
    start,end,old=block(text,needle)
    new=transform(old)
    if chain:
        old=old.replace('if ', 'elif ',1)
    return text[:start]+new+old+text[end:]

def change(name, fn):
    path=package/(name+'.py')
    value=fn(path.read_text())
    compile(value,str(path),'exec')
    path.write_text(value)

def records(s):
    line='from .native_blast_database_contracts import NATIVE_BLAST_DATABASE_REQUESTED_JOB_SCHEMA\n'
    s=s.replace(line,line+standard(line))
    s=s.replace('    NATIVE_BLAST_DATABASE_REQUESTED_JOB_SCHEMA]}','    NATIVE_BLAST_DATABASE_REQUESTED_JOB_SCHEMA, NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA]}')
    return duplicate(s,"if 'native_blast_database' in job:",chain=True)
change('practical_execution_records',records)
change('practical_execution_operations',lambda s: duplicate(s,"if 'native_blast_database' in assignment['requested_job']:"))

def pbs(s):
    s=s.replace("('native_blast_database_plan_path','native_blast_database_plan_sha256')", "('native_blast_database_plan_path','native_blast_database_plan_sha256','native_blast_standard_database_plan_path','native_blast_standard_database_plan_sha256')")
    s=duplicate(s,"if 'native_blast_database' in logical:")
    s=s.replace("('observe_execution','read_output','native_blast_database_attempt')", "('observe_execution','read_output','native_blast_database_attempt','native_blast_standard_database_attempt')")
    start,end,old=block(s,'    if database_attempt:')
    new=standard(old).replace('if database_attempt:', 'if standard_database_attempt:')
    s=s[:start]+"    standard_database_attempt='native_blast_standard_database' in assignment['requested_job']\n"+new+s[start:]
    s=duplicate(s,"if request['mode']=='native_blast_database_attempt':",transform=lambda v:standard(v).replace('not database_attempt','not standard_database_attempt'),chain=True)
    start,end,old=block(s,'        if database_attempt:')
    s=s[:start]+standard(old).replace('if database_attempt:', 'if standard_database_attempt:')+s[start:]
    s=s.replace('if not database_attempt:raise\n','if not (database_attempt or standard_database_attempt):raise\n')
    s=duplicate(s,'def validate_native_blast_database_resource(configuration):')
    s=s.replace("set(configuration) - expected - {'native_blast_database'}", "set(configuration) - expected - {'native_blast_database', 'native_blast_standard_database'}")
    s=duplicate(s,"if 'native_blast_database' in configuration:")
    s=duplicate(s,"if 'native_blast_database' in assignment['requested_job']:")
    s=duplicate(s,'def authenticate_native_blast_database_attempt(self, assignment, execution_id, *, attempt_id=None, **identity):')
    return s
change('practical_pbs_operations',pbs)

def progress(s):
    start=s.index("    database = assignment['requested_job'].get('native_blast_database')")
    end=s.index("    native_blast =",start)
    s=s[:start]+standard(s[start:end])+s[start:]
    s=duplicate(s,"if 'native_blast_database' in assignment['requested_job']:")
    s=duplicate(s,"if 'native_blast_database' in target['assignment']['requested_job']:",transform=lambda v:standard(v).replace('native_blast_standard_database_result_worker.calculate_standard_blast_database_sheets','native_blast_standard_database_calculators.calculate_standard_blast_database_sheets'))
    s=s.replace("or 'native_blast_database' not in target['assignment']['requested_job']):\n            return False", "or not ({'native_blast_database', 'native_blast_standard_database'} & set(target['assignment']['requested_job']))):\n            return False")
    return duplicate(s,'def authenticate_native_blast_database_attempt(self, target):')
change('execution_progress',progress)

def episodes(s):
    line='from .native_blast_database_acquisition import is_native_blast_database_target\n'
    s=s.replace(line,line+standard(line))
    s=duplicate(s,"if 'native_blast_database' in configuration and kind != 'hpc':")
    start=s.index('        self.native_blast_database_results = self.native_blast_database_returns = None')
    _,end,_=block(s,"if any(configuration.get('native_blast_database') for configuration in self.resources.values()):")
    s=s[:start]+standard(s[start:end])+s[start:]
    start=s.index("            database = self.resources[resource_id].get('native_blast_database')")
    _,end,_=block(s,'            if database:')
    s=s[:start]+standard(s[start:end])+s[start:]
    # Original input custody applies to each selected native database family.
    lines=s.splitlines(keepends=True)
    out=[]
    for line in lines:
        out.append(line)
        if 'from .native_blast_database_result_publication import validate_native_job_inputs' in line or 'validate_native_job_inputs(self.store,' in line:
            out.append(standard(line))
    s=''.join(out)
    # Each native6 dispatch block has a disjoint, explicit standard peer.
    offsets=[]
    position=0
    for line in s.splitlines(keepends=True):
        stripped=line.strip()
        if stripped.startswith('if ') and ('self.native_blast_database_' in stripped or 'is_native_blast_database_target(' in stripped or "configuration.get('native_blast_database')" in stripped):
            if not stripped.startswith("if any(configuration.get('native_blast_database')"):
                _,end,old=block(s[position:],line)
                if not any(a<=position<b for a,b,_ in offsets):
                    offsets.append((position,position+end,old))
        position+=len(line)
    for start,end,old in sorted(offsets,reverse=True):
        s=s[:start]+standard(old)+s[start:]
    s=s.replace("'native_blast_bundle_v1', 'native_blast_database_bundle_v1'", "'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1'")
    return s
change('execution_episodes',episodes)

def communication(s):
    s=s.replace('    native_blast_sources = None\n','    native_blast_sources = None\n    standard_blast_sources = None\n')
    s=s.replace('nonlocal native_blast_sources','nonlocal native_blast_sources, standard_blast_sources')
    return duplicate(s,'if isinstance(source, str) and source.startswith("execution_blast_database_"):',transform=lambda v:standard(v).replace('native_blast_sources','standard_blast_sources'))
change('communication',communication)

def domain(s):
    start=s.index('        "native_blast_database": obj(')
    end=s.index('        "native_infernal":',start)
    new=standard(s[start:end]).replace('["psiblast", "deltablast", "rpsblast", "rpstblastn", "blastn_vdb", "tblastn_vdb"]','["blastn", "blastp", "blastx", "tblastn", "tblastx"]').replace('["sequence", "msa_master", "pssm_master"]','["sequence", "pssm_master"]').replace('["sequence", "profile_model", "vdb_member"]','["sequence"]')
    s=s[:start]+new+s[start:]
    line='REASONING_SCHEMA["properties"]["observations"]["items"]["properties"].pop("native_blast_database", None)\n'
    return s.replace(line,line+standard(line))
change('domain',domain)

def state(s):
    start=s.index('            native_database = data.get("native_blast_database")')
    end=s.index('            native_pairwise =',start)
    new=standard(s[start:end]).replace("'msa': 'msa_master', ", '').replace("('profile_match' if native_database['reference_axis_kind'] == 'profile_model' else 'comparison')", "'comparison'")
    return s[:start]+new+s[start:]
change('state',state)
for name in ('evidence_geometry','evidence_axis_contracts','alignment_site_native','blast_result_views'):
    def dispatch(s):
        result=[]
        lines=s.splitlines(keepends=True)
        i=0
        while i<len(lines):
            if lines[i].lstrip().startswith('if ') and ".get('native_blast_database') is not None:" in lines[i]:
                indent=len(lines[i])-len(lines[i].lstrip())
                j=i+1
                while j<len(lines) and (not lines[j].strip() or len(lines[j])-len(lines[j].lstrip())>indent):j+=1
                old=''.join(lines[i:j]);result.extend([standard(old),old]);i=j
            else:result.append(lines[i]);i+=1
        return ''.join(result)
    change(name,dispatch)
change('infernal_result_presentation',lambda s:s.replace('("native_blast_database", "native_blast_database_observation_v1"),','("native_blast_database", "native_blast_database_observation_v1"),\n                    ("native_blast_standard_database", "native_blast_standard_database_observation_v1"),'))
print('Installed additive branches in',len(names),'shared modules')
