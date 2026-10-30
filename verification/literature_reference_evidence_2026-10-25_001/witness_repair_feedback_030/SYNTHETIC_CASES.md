# Synthetic witness cases

These strings are test data, not scientific measurements.

| Actual selected text | Nominated text | Actual UTF8 bytes | Nominated UTF8 bytes | First mismatching relative byte |
| --- | --- | --- | --- | --- |
| abc | abd | 3 | 3 | 2 |
| abc | abcd | 3 | 4 | 3 |
| abcd | abc | 4 | 3 | 3 |
| Δµ | Δμ | 4 | 4 | 2 |
| é | ê | 2 | 2 | 1 |
| é | e + combining acute | 2 | 3 | 0 |
| Δ | Δx | 2 | 3 | 2 |

The same case will use both original/text representations with distinct
artifact identities and multibyte prefixes before the selected span. A separate
case has a nomination containing a lone surrogate: selected source text is
valid, nomination UTF8 length and mismatch byte remain unknown, and the original
source_quote_mismatch is retained.

Before-content failures cover missing receipt, outside scope, outside assigned
source ancestry, unknown source, unavailable representation, out-of-bounds and
nonempty/span/index guards, plus selected invalid UTF8 and split-codepoint spans.
They must not carry selected text or mismatch detail.

The integration fixture chooses its repair explicitly from a predetermined
correct argument object. The operation implementation never mutates the failed
arguments, retries or selects a scientifically meaningful span. Counts after
closure: four selected actions, one invalid population, one successful
population, three controller observations, one saved numerical sheet, one
admitted native typed-return subset, and zero annotation credit.

Replay uses the actual DecisionSource.execute saved-result branch with source
reading and dispatch forbidden. It verifies exact recorded detail and a separate
legacy failure without detail, without additional observations or row changes.
