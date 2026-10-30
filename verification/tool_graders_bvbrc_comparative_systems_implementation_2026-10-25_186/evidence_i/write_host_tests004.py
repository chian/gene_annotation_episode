from pathlib import Path
p=Path('tests/test_bvbrc_comparative_systems_tool_info.py')
s=p.read_text().replace("{'api': family.resource_tool_contracts()['api']}", "{'api': [item for item in family.resource_tool_contracts() if item['resources'] == 'api']}")
s=s.replace("absent.resource_tool_contracts()['api']", "absent.resource_tool_contracts()")
p.write_text(s)
