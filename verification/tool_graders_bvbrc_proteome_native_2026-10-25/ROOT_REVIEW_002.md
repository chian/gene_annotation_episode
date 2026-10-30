# Root review and canonical record keys

Root read both complete parser/validator modules and reproduced two missing
saved-projection relationships. A reference key could name another ordinal;
an association key could name another comparison/ordinal. The parser generated
correct keys, but validate_native_projection accepted these altered values.
ROOT_RELATIONSHIP_REVIEW_001.json preserves the pre-fix reproduction and hash.

The validator now requires reference_row_key=ref_genome/row/{row_ordinal} and
association_key={track_key}/row/{reference_row_ordinal}. This changes no frozen
schema, native value, numerical formula, custody responsibility or episode.
Eight new cases cover both formats and mismatched ordinals/comparison keys.

ROOT_REGRESSION_004.xml retains 92 passes and two test failures: the new
comparison-key example accidentally duplicated an existing association key,
so the older duplicate check rejected it before the newly expected check. The
example now uses absent comparison 9 to isolate the new relationship check.
ROOT_REGRESSION_005.xml records all94 tests passing in2.79s. No production
validation was weakened to satisfy that expectation. The original86-pass
component receipt and source hashes remain unchanged as historical evidence.

This remains a synthetic native-format component. No complete directional
reports, actual executed input inventory, numerical sheet/calculator, deployed
producer compatibility, live API output or complete episode binding is claimed.
The new schema asset still needs package-data integration. The original active
Workflow consumers do not import these new modules; their sources stay frozen.
