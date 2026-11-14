"""Original instructions for selected scientific tool information retrieval."""

INSTRUCTIONS = """Retrieve actual callable tools for the parent's desired investigation.
Return only {"tools":[actual callable names]} under the supplied schema. Inspect
the complete supplied map: names, descriptions and exact input contracts. Select
all operations useful for carrying out this investigation with the available
capabilities, including prerequisites and reading/checking their real results.
Keep the set relevant to this investigation. Do not select an operation merely
because its description shares a word. Source/data reading can be useful, but a
scientific data question does not itself request an unrelated publication search
or literature-reading investigation. There is no fixed group or selection quota.
Do not invent tools, capabilities, tool arguments or replacements for an absent
operation. When a specialized capability is absent, select only actually useful
available operations; an empty selection is permitted. This retrieval supplies
information: do no scientific work, choose no hypothesis, job, resource, action,
child episode or timer, and return no findings, plan or scientific judgment.
"""
TOOL_INFO_INSTRUCTIONS = """Select actual tool/resource variants for the parent's desired investigation.
Return only {"child_tool_info":[{"name":actual_name,"resources":actual_resource_kind}]}
under the supplied schema. Inspect the complete supplied metadata map of actual
names, descriptions and resource kinds. Select all useful available operations,
including prerequisites and reading their real results, with no fixed bundle or
quota. A repeated name with another resource is a different variant: preserve
the exact pair. Do not write descriptions, instructions, arguments or substitutes
for missing capabilities. The host supplies each selected tool's frozen real
instructions and invocation contract to the child. This call retrieves
information; perform no scientific work and choose no hypothesis, child, job,
timer or execution action. An empty selection is allowed.
Source/data reading can be relevant without requesting an unrelated publication
search or literature-reading investigation. Keep tool selection within the
parent's actual desired investigation and the receiver's available operations.
"""


