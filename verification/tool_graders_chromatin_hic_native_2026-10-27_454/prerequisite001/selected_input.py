"""Bounded primary-source/prerequisite discovery; no installation."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import subprocess
import urllib.request

ROOT = Path.cwd()
def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def fetch(url, name, headers=None):
    request_headers = {'User-Agent': 'hictk-native-fixture-verification', **(headers or {})}
    save(name + '.request.json', {'url': url, 'headers': request_headers})
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
        save(name + '.response.json', {'url': response.url, 'status': response.status,
             'headers': dict(response.headers), 'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data)})
    (ROOT / name).write_bytes(data)
    return data

env = {'platform': platform.platform(), 'machine': platform.machine(), 'python': platform.python_version(),
       'executables': {key: shutil.which(key) for key in ['hictk','g++','clang++','cmake','ninja','conan','docker','skopeo','java','ldd']}}
save('ENVIRONMENT.json', env)
for name in ['g++','clang++','cmake','ninja']:
    if env['executables'][name]:
        done = subprocess.run([env['executables'][name], '--version'], capture_output=True, text=True)
        save(name + '.version.json', {'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr})
release = json.loads(fetch('https://api.github.com/repos/paulsengroup/hictk/releases/tags/v2.2.0', 'release.json'))
fetch('https://raw.githubusercontent.com/paulsengroup/hictk/473017312558cd805f470722c2c91a03b91df807/docs/installation.rst', 'installation.rst')
fetch('https://raw.githubusercontent.com/paulsengroup/hictk/473017312558cd805f470722c2c91a03b91df807/docs/installation_source.rst', 'installation_source.rst')
print(json.dumps({'assets': [{key: item.get(key) for key in ['id','name','size','digest','browser_download_url']} for item in release['assets']], 'environment': env}))
