# Scientific labels and private operands — explicit unresolved design detail

No blanket numeric-label suppression. These labels carry scientific meaning and
must survive when actually supplied as the requested bound meaning:

| Bound role | Constructed value | Proposed display |
| --- | --- | --- |
| variant | K426A | K426A |
| genotype | ΔgeneX::kan | ΔgeneX::kan |
| construct_variant | His-tagged protein residues 1–253 | His-tagged protein residues 1–253 |
| condition | 37 °C; pH 7.4 | 37 °C; pH 7.4 |
| normalization | same-blot tagged WT reference | same-blot tagged WT reference |
| endpoint | immunoblot protein-band signal | immunoblot protein-band signal |

These are different from automatically expanding source/witness records such as
`At 37 °C the K426A band was 0.64 and WT was 1.00 on the same blot.` The latter
must not appear in reported_ratio-only parent STEERING. Neither may a source
measurement label `numerator 0.64; reference 1.00` or whole sheet be expanded.

Exact008 gives the receiver typed role refs and meaning_statuses. The actual
native records label those roles with comparison.meaning.value; they do not have
anchors or a distinction between a compact identity/context label and a copied
paragraph. The typed return contains no witness geometry or numerical-token
location. Therefore a renderer given only exact008 rows and those reference
records cannot prove which arbitrary numeric-bearing free string is a standalone
scientific definition. Numeric regex filtering would lose essential meanings;
printing every arbitrary label could leak unrequested operands. This is an actual
information limitation, not permission to add a new return field or reinterpret
scientific unknown as zero.

Proposed implementation for root review has two parts:

1. Dedicated rendering consumes only exact requested rows and explicitly bound
   role labels. Generic recursion expands none of the source-ratio sheet,
   measurement references, witness/source prose or private images. Unrelated
   independently received source records remain eligible under their own rules.
2. Resolve each actual requested role label through host-side saved-only custody
   metadata, never original source/image IO or a model call. The new rendering
   helper can read the native saved payload through repository.read solely to
   select labels and compare their existing authenticated witnesses with retained
   numeric loci; it does not emit extraction, raw literals, private values,
   witnesses or additional components. Returned numbers still come only from the
   actual admitted subset. This is bookkeeping validation/filtering, not delivery
   of the whole sheet to the parent.

This requires a proposed additional, small edit to
literature_reference_parent_prompt.py: include the host-filtered
literature_ratio_source_return_meanings in its _steering input whitelist. The
current whitelist drops any new sibling state field, so omitting that edit would
make this plan fictitious. No edit has been made; root must include it in the
later ownership release or choose another reviewed information path.

For a text definition, when the exact meaning value occurs uniquely in its
authenticated witness, derive that value's actual subspan. For an image
definition, use its supplied source/frame/region as the retained location without
claiming OCR text authentication. Distinct sources/frames and disjoint same-view
regions remain distinct. A witness/raw operand overlap is reason to avoid
automatically rendering the broad quote, not evidence that the meaning is false.
Known labels such as the six above are emitted exactly from their separately
selected definition spans/regions. A broad copied paragraph or measurement label
containing raw operands is withheld; keep its known/unknown/conflicting status and
display `source-bound definition retained for scoped access`, never `unknown`
merely because display was withheld. Parent may select an ordinary scoped read
if that detail matters; no mandatory repair, hidden source action or gate.

This finite proposal still needs root feedback on ambiguous broad-image labels
whose geometry covers both a necessary numeric condition and the printed signal.
No deterministic region check can determine subregion semantics from that box.
It must retain the known definition/status and withhold the ambiguous display,
or a more precise source selection must be explicitly requested. It must not
remove K426A/37 °C/residue boundaries just because they contain digits. Do not
treat this proposal as settled or code it before the root's exact design review.

Root's subsequent direction accepts saved-only custody filtering in this bounded
role and requires these additional cases. These refinements are part of the final
design, not an implementation claim:

- Collect numeric loci from EVERY nominated numerator AND reference candidate
  across the actual saved selected roster, including conflicting/ambiguous and
  different-quantity representations. Do not pick a primary candidate or use only
  the scalar-producing reading. Measurement labels remain withheld altogether.
- For retained JATS `64% (K426A)`, the numeric locus is `64%`; K426A is an
  essential variant label inside the expression and must survive. Use the
  already validated retained expression's literal percent token to derive its
  paragraph-character subrange; do not hide the whole expression range.
- JATS expression positions are Unicode characters in the retained paragraph.
  Generic text_span coordinates are original UTF8 bytes. Never compare those
  integers as the same coordinate system. If an exact generic witness quote
  appears uniquely in that retained paragraph, its label's unique substring can
  be located in paragraph characters and compared there. Otherwise retain the
  actual source/representation byte-span coordinate system or return a display
  limit; do not invent XML-to-paragraph offsets or reacquire/reparse source bytes.
- For an exact compact definition witnessed outside numeric loci, retain digits
  verbatim: K426A; residues1–253;37°C/pH7.4. No numeric stripping or implicit
  interpretation model. Broad copied prose overlapping the candidate operand
  loci stays withheld, with its original known status intact. If a compact label
  cannot be located unambiguously outside the raw loci, keep the known status and
  explicit retained-for-scoped-access display state. This display limitation
  does not alter C4 admission, numerical evidence or source access.
