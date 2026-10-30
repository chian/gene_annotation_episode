# Spillover matrix locator clarification

Additive clarification to013's preparation reader port, settled before coding.

`read_fcs_spill_matrix(raw, *, source, locator, channels)` uses exactly:

```
locator = {dataset_position: nonnegative integer, keyword: "spill" | "spillover"}
```

Integers exclude booleans. The dataset position equals `source.dataset_position`
and the selected recipe's matrix dataset. The keyword equals the explicitly
selected recipe keyword; there is no automatic preference between the two.
`channels` is the actual parent parse's ordered Channel rows, including their
domain_key, all from the same domain. Do not infer channel names or ordering.
The actual source bytes and source identity remain authoritative. No other
preparation, numerical or execution contract changes.
