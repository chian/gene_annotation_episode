"""Acquire the explicitly selected upstream release image metadata and source."""
from pathlib import Path
import hashlib
import json
import tarfile
import urllib.error
import urllib.request

ROOT=Path.cwd()
def save(name, value):
    (ROOT/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
def fetch(url, name, headers=None, expected_sha256=None):
    headers={'User-Agent':'hictk-native-fixture-verification', **(headers or {})}
    save(name+'.request.json', {'url':url,'headers':{k:('public_registry_token_redacted' if k=='Authorization' else v) for k,v in headers.items()}})
    try:
        response=urllib.request.urlopen(urllib.request.Request(url, headers=headers),timeout=60)
    except urllib.error.HTTPError as exc:
        response=exc
    with response:
        data=response.read()
        digest=hashlib.sha256(data).hexdigest()
        save(name+'.response.json', {'url':response.url,'status':response.status,'headers':dict(response.headers),'sha256':digest,'size_bytes':len(data)})
        (ROOT/name).write_bytes(data)
        if response.status !=200: raise RuntimeError(f'HTTP {response.status}: {url}')
    if expected_sha256 is not None and digest!=expected_sha256: raise RuntimeError('upstream_digest_mismatch')
    return data
base='https://raw.githubusercontent.com/paulsengroup/hictk/473017312558cd805f470722c2c91a03b91df807/'
fetch(base+'Dockerfile','Dockerfile')
fetch(base+'docs/installation_src.rst','installation_src.rst')
fetch(base+'conanfile.py','conanfile.py')
fetch('https://codeload.github.com/paulsengroup/hictk/tar.gz/473017312558cd805f470722c2c91a03b91df807','hictk-pinned-source.tar.gz')
with tarfile.open(ROOT/'hictk-pinned-source.tar.gz') as archive:
    archive.extractall(ROOT/'source',filter='data')
token_url='https://ghcr.io/token?service=ghcr.io&scope=repository:paulsengroup/hictk:pull'
with urllib.request.urlopen(urllib.request.Request(token_url,headers={'User-Agent':'hictk-native-fixture-verification'}),timeout=60) as response:
    token=json.load(response)['token']
save('PUBLIC_REGISTRY_AUTH.json', {'token_url':token_url,'credential_source':'anonymous_public_registry_token','token_retained':False})
headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json'}
index=json.loads(fetch('https://ghcr.io/v2/paulsengroup/hictk/manifests/2.2.0','image-index.json',headers))
selected=[entry for entry in index['manifests'] if entry.get('platform',{}).get('os')=='linux' and entry.get('platform',{}).get('architecture')=='amd64']
if len(selected)!=1: raise RuntimeError('ambiguous_amd64_image')
descriptor=selected[0]
manifest=json.loads(fetch('https://ghcr.io/v2/paulsengroup/hictk/manifests/'+descriptor['digest'],'image-manifest.json',headers,descriptor['digest'].split(':')[1]))
fetch('https://ghcr.io/v2/paulsengroup/hictk/blobs/'+manifest['config']['digest'],'image-config.json',headers,manifest['config']['digest'].split(':')[1])
save('SELECTED_IMAGE.json', {'upstream':'ghcr.io/paulsengroup/hictk:2.2.0','descriptor':descriptor,'layers':manifest['layers']})
print(json.dumps({'descriptor':descriptor,'layers':manifest['layers']}))
