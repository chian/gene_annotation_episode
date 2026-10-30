from pathlib import Path
p=Path('tests/test_bvbrc_comparative_systems_tool_info.py')
s=p.read_text().replace('family.resource_tool_catalogs()', "{'api': family.resource_tool_contracts()['api']}")
s=s.replace("absent.resource_tool_catalogs()['api']", "absent.resource_tool_contracts()['api']")
p.write_text(s)
p=Path('tests/test_bvbrc_comparative_systems_publication.py')
s=p.read_text().replace('from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import validate_saved_comparative_systems_projection','from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import assemble_projection')
s=s.replace("    result.update(sheet=None, components=None, status=state)\n    for fact in result['facts'].values():\n        fact.update(values=[], status='unavailable')", "    result = assemble_projection(None, None, requested_form=args['requested_form'],\n        retained_requirements=[], retained_diagnostics=[], failure_status=state)")
p.write_text(s)
