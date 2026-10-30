from pathlib import Path
import hashlib,json,shutil
repo=Path('/home/chia/repos/gene_annotation_episode')
work=Path('/tmp/research-notes-recovery-20261021')
old=repo/'research/slotted_process_library/background/pre_curation_20261021'
stage=work/'replay';stage.mkdir(exist_ok=True)
for f in old.iterdir():
 if f.is_file():shutil.copyfile(f,stage/f.name)
shutil.copyfile(work/'README-original.md',stage/'README.md')
# RUNTIME_INTEGRATION does not affect the three recovered outputs.
(stage/'RUNTIME_INTEGRATION.md').write_text('# Replay placeholder for unrelated output\n')
commands=['call_Imave8ryYYQ5drDtDIjTRpwU','call_zLqJs4aW5rBoHtjZebipyv7r','call_GSSR3VWg6f9sE1zbLNyqBnzl']
for call in commands:
 command=(work/(call+'.sh')).read_text()
 code=command.split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
 code=code.replace("Path('research/slotted_process_library')",'Path('+repr(str(stage))+')')
 code=code.replace("Path('research/slotted_process_library/CURRENT_SLOT_SOURCES.md')",'Path('+repr(str(stage/'CURRENT_SLOT_SOURCES.md'))+')')
 exec(compile(code,str(work/(call+'.sh')),'exec'),{})
assert hashlib.sha256((stage/'CURRENT_SLOT_SOURCES.md').read_bytes()).hexdigest()=='6b6acf7f20c891ed01f46e95e9fa831a9db37bf01a4132a2213fdfc1b6f2c5a0'
print('Recovered table matches independently retained pre-curation hash.')
