# Final003 correction to the intermediate029 description

This additive record supersedes the markup-normalization and final-demo
statements in IMPLEMENTATION_AND_LIMITS_001.md. The intermediate source manifest,
diff, test logs and demos remain preserved. Only released027 and final003 exact
dependency dictionaries are supported; intermediate001/002 are not promoted to
supported scientific-record generations.

Two concrete contrasts motivated the bounded hardening after joined002 finished:

1. Encoded `&lt;between 2.1 and 2.9&gt;` before the first amount was previously
   stripped as arbitrary tag-shaped text when classifying the second amount.
   That could wrongly authorize positive coordination.
2. With an unfamiliar first endpoint containing
   `<span style="color:red;">low</span>`, the shared raw-context candidate test
   treated the CSS semicolon as a delimiter and admitted both endpoints, while
   the native visible-context route rejected both. Normal spaces around the
   selected numbers were used, so lexical clipping did not mask this defect.

Final candidate matching recognizes a finite inline-format-tag fragment when
finding delimiters. Delimiter punctuation inside those tags does not conceal a
range candidate. The positive classifier retains attribute-bearing tag bytes;
they cannot authorize coordination in the shared raw-context path. It ignores
only bare, attribute-free `i`, `em`, `b`, `strong`, `span`, `sup`, `sub`, `italic`
and `bold` tags, including their closing/self-closing forms. It performs no
second entity decoding. A nearest `between` lying inside an unmatched angle-tag
fragment is unresolved. A completed allocation whose addition clause is not
recognized is unresolved, rather than classifying its digit vessel count as a
numerical endpoint.

These changes operate only on the syntactic candidate/classification view.
Actual source bytes, witnesses and both existing context functions are unchanged.
Other scalar guards remain independent. Both CSS-range endpoints now reject on
both routes; bare-markup positive allocations remain supported. Arbitrary encoded
tag-looking and attribute-bearing scope text cannot authorize positive escape.

This is a finite markup/punctuation grammar. Quote-delimited HTML attributes
containing literal angle brackets, arbitrary tag vocabularies and general
linguistic sentence segmentation are not established. In the native route,
actual inline markup is already removed before the shared classifier by the
unchanged field reader; this does not license removing encoded tag-looking
source prose a second time. Conservative shared-path rejection of unsupported
attribute-bearing positive allocations is an explicit limitation.

Final owned files/hashes and complete delta are SOURCE_MANIFEST_002.json and
SOURCE_DELTA_002.patch. FOCUSED_FINAL_TESTS_003.log is the final-generation
connected check group. CONTROLLED_NOMINAL_DEMO_003.json is the final-generation
ordinary-loop demonstration. Joined001/002 logs and demonstrations001/002 are
intermediate engineering history; counts overlap and must not be added.
