"""Two explicit bounded public input captures, never a scientific result stub."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

import pytest


pytestmark=pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ,reason='requires bounded529')
SELECTED=(('gene2','https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=gene&id=2&retmode=xml&tool=gene-annotation-episode','application/xml'),
    ('addgene50005','https://www.addgene.org/50005/sequences/','text/html'))
LIMIT=4*1024*1024


@pytest.mark.parametrize('name,url,accept',SELECTED,ids=['selected_gene2_xml','selected_addgene50005_html'])
def test_capture_selected_original_public_entity(name,url,accept):
    directory=Path(os.environ['HMMER529_ATTEMPT'])/'sequence-support-native739'
    directory.mkdir(exist_ok=True)
    data={'selected_url':url,'request_method':'GET','byte_limit':LIMIT,'transport_timeout_seconds':90,
        'attempts':1,'retrieved_at':datetime.now(timezone.utc).isoformat(),
        'status':None,'effective_url':None,'headers':[],'body_complete':False,'failure_code':None}
    body=b''
    request=urllib.request.Request(url,headers={'Accept':accept,'User-Agent':'gene-annotation-episode/0.2'})
    response=None
    try:
        try:response=urllib.request.urlopen(request,timeout=90)
        except urllib.error.HTTPError as error:
            response=error
            data['failure_code']='provider_http_'+str(error.code)
        with response:
            data.update(status=response.status,effective_url=response.geturl(),headers=list(response.headers.items()))
            body=response.read(LIMIT+1)
            data['body_complete']=len(body)<=LIMIT
            if not data['body_complete']:
                body=body[:LIMIT]
                data['failure_code']='provider_response_byte_limit'
    except Exception as error:
        data['failure_code']='provider_transport_failed'
        data['exception_type']=type(error).__name__
        data['exception_message']=str(error)
    data.update(size_bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),
        entity_file=name+'.entity',scientific_native_success=(data['status']==200 and data['body_complete']))
    (directory/(name+'.entity')).write_bytes(body)
    (directory/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
    # This checks capture custody, not provider availability/native parsing.
    assert len(body)<=LIMIT
    assert data['attempts']==1
    assert hashlib.sha256((directory/(name+'.entity')).read_bytes()).hexdigest()==data['sha256']
