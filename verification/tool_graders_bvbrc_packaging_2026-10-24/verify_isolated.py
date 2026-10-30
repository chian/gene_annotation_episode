import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from gene_annotation_episode.bvbrc_application_definitions import REQUIRED_APPLICATION_IDS,get_application_spec
import gene_annotation_episode.bvbrc_application_definitions as definitions
rows=[]
for name in REQUIRED_APPLICATION_IDS:
    spec=get_application_spec(name)
    assert hashlib.sha256(spec['source']['content'].encode()).hexdigest()==spec['source']['sha256']
    rows.append({'required_id':name,'native_id':spec['native_id'],'sha256':spec['source']['sha256']})
assert len(rows)==24
assert Path(definitions.__file__).is_relative_to(sys.argv[1])
print(json.dumps({'loaded_from_isolated_wheel':True,'applications':rows},sort_keys=True))
