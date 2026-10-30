# Electrical components179: inverse-unit boundary correction003

This additive same-workload correction addresses the two remaining real defects identified in root183 probe002. Manifest002 did not establish adequate closing-parenthesis handling: source suffixes `±0.2 pA)⁻¹` and `±0.2 pA)−1` were still accepted as a plain pA measurement. Earlier002 artifacts and root's failed probes remain historical evidence; no acceptance is claimed for them.

The one production change extends the existing unit-continuation guard after optional closing parentheses to recognize ordinary/superscript negative exponent forms, and every superscript numeral including¹. It does not strip the closing punctuation or rewrite units. Inverse/power continuations return the existing repairable `partial_electrical_unit` error. Ordinary closing punctuation remains accepted. No schema, public interface, numerical formula, TASK, source interpretation or scientific value changes.

Only the owned reader and test files changed. CORRECTION_DIFF_003.patch records this small change against retained002bytes. Calculations and prompt hashes remain unchanged. No shared production, integration, source paper, provider log, goal or instruction file was touched.

TESTS_006.xml/log:142passed,0failed,0errors,0skipped. The focused synthetic file includes the existing125cases plus17targeted positive/negative closure cases. Do not add historical overlapping test totals. INVERSE_UNIT_CORRECTION_PROBE_003.json replays all eight root183arrangements and two ordinary-punctuation controls; all ten expected acceptance results pass. All four owned files compile. Root independent re-probing/review remains pending, and the increment still establishes neither episode integration nor A105 adequacy.
