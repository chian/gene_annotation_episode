from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
from gene_annotation_episode.bvbrc_comparative_systems_bundle_adapter import implementation_sha256
owned=['gene_annotation_episode/'+name+'.py' for name in ('bvbrc_comparative_systems_tool_info','bvbrc_comparative_systems_returns','bvbrc_comparative_systems_host_inputs','bvbrc_comparative_systems_publication','bvbrc_appservice_adapters','api_service_execution','bvbrc_appservice_host','bvbrc_appservice_publication','execution_episodes')]
owned += ['tests/test_bvbrc_comparative_systems_'+name+'.py' for name in ('episode_flow','returns','host_inputs','publication','tool_info')]
owned += [str(path) for path in sorted(Path('tests/fixtures/bvbrc_comparative_systems_integration').rglob('*')) if path.is_file()]
value={'captured_at':datetime.now(timezone.utc).isoformat(),'candidate':str(Path.cwd()),'provider_pin':implementation_sha256(),'files':[{'path':p,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest(),'bytes':Path(p).stat().st_size} for p in owned], 'capture_note':sys.argv[2]}
Path(sys.argv[1]).write_text(json.dumps(value,indent=2)+'\n')
print({'file':sys.argv[1],'count':len(owned),'provider_pin':value['provider_pin']})
