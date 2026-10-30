# Exact host provider return identity

Current `AppServicePublications._grade` compares `result['adapter_id']` and
`result['adapter_version']` with the immutable selected adapter before saving
sheet/components. Therefore `SCHEMAS_004.json` adds exactly these required
constant fields to ProviderResult: `adapter_id='bvbrc_fastqutils'` and
`adapter_version='2'`. Apart from schema `$id`, this is the only difference from
003. Frozen002/003 and A/B contracts are unchanged.

The complete provider return is `{adapter_id, adapter_version, status, facts,
missing_requirements, diagnostics, sheet, components}`. The first two are not
optional or supplied by a later wrapper. Native data failures remain local
requirements/diagnostics; malformed API argument shape or contradictory byte
binding raises FastqUtilsContractError before projecting fabricated values.
The already retained selected acquisition records remain authoritative.
