"""Extract only the selected official image's native binary, then verify it."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tarfile
import urllib.request

ROOT=Path.cwd()
PACKET=ROOT.parent
def save(name,value): (ROOT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def pin(path):
    path=Path(path); data=path.read_bytes()
    return {'path':str(path),'resolved_path':str(path.resolve()),'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}
descriptor=json.loads((PACKET/'prerequisite002/SELECTED_IMAGE.json').read_text())
config=json.loads((PACKET/'prerequisite002/image-config.json').read_text())
assert config['config']['Labels']['org.opencontainers.image.revision']=='473017312558cd805f470722c2c91a03b91df807'
layer=descriptor['layers'][3]
assert layer['digest']=='sha256:c7bf16a195dfd733b95757f7243c08b0f27830d5edb31cac9b54fc68bcc40821'
url='https://ghcr.io/v2/paulsengroup/hictk/blobs/'+layer['digest']
save('ACQUISITION_REQUEST.json', {'url':url,'expected_descriptor':layer,'image_manifest':descriptor['descriptor'],'selected_member':'usr/local/bin/hictk','source_revision':'473017312558cd805f470722c2c91a03b91df807'})
with urllib.request.urlopen('https://ghcr.io/token?service=ghcr.io&scope=repository:paulsengroup/hictk:pull',timeout=60) as response: token=json.load(response)['token']
with urllib.request.urlopen(urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'User-Agent':'hictk-native-fixture-verification'}),timeout=60) as response:
    data=response.read()
    save('ACQUISITION_RESPONSE.json',{'status':response.status,'headers':dict(response.headers),'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)})
assert hashlib.sha256(data).hexdigest()==layer['digest'].split(':')[1]
assert len(data)==layer['size']
archive=ROOT/'hictk-release-layer.tar.gz'; archive.write_bytes(data)
with tarfile.open(archive) as source:
    members=[{'name':entry.name,'size':entry.size,'type':entry.type.decode('ascii')} for entry in source.getmembers()]
    save('LAYER_MEMBERS.json',members)
    member=source.getmember('usr/local/bin/hictk')
    assert member.isfile()
    native=ROOT/'hictk'
    native.write_bytes(source.extractfile(member).read())
    native.chmod(0o555)
save('BINARY_PIN.json',pin(native))
env={**os.environ,'HICTK_NO_TELEMETRY':'1'}
commands={
    'version':[str(native),'--version'],
    'help':[str(native),'--help'],
    'load_help':[str(native),'load','--help'],
    'dump_help':[str(native),'dump','--help'],
    'metadata_help':[str(native),'metadata','--help'],
    'validate_help':[str(native),'validate','--help'],
    'ldd':['/usr/bin/ldd',str(native)],
}
for name,argv in commands.items():
    proc=subprocess.run(argv,env=env,capture_output=True,text=True)
    save(name+'.command.json',{'argv':argv,'environment_overrides':{'HICTK_NO_TELEMETRY':'1'},'returncode':proc.returncode})
    (ROOT/(name+'.stdout.txt')).write_text(proc.stdout)
    (ROOT/(name+'.stderr.txt')).write_text(proc.stderr)
    if proc.returncode: raise RuntimeError(f'{name}: exit {proc.returncode}')
assert '2.2.0' in (ROOT/'version.stdout.txt').read_text()
libraries=[]
for token in (ROOT/'ldd.stdout.txt').read_text().split():
    if token.startswith('/') and Path(token).is_file(): libraries.append(pin(token))
save('RUNTIME_DEPENDENCIES.json',libraries)
print(json.dumps({'binary':pin(native),'version':(ROOT/'version.stdout.txt').read_text(),'runtime_files':libraries}))
