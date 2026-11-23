# A102: the root's grouping of candidates, applied by the head

Status: design agreed with the owner on 2026-11-23 ("let's go with it. I don't have a better idea for now. I would prefer
something more absolute, but let's go with this for now"). Not built when this was written.

## Why

A102 names its product candidates by the names of the proteins its structure matches, so one function arrives under several
names. Each name's annotation score is then the score of a spelling, not of the function, and the head's two leading candidates
can be two spellings of one thing. The owner's rulings:

- Only the root decides which candidates are the same function; an arm merges nothing by itself ("if all different arms are
  merging then the later consolidation is even harder b/c different arms might consolidate differently").
- "the purpose is to make the arms annotation scores honest. improving that honesty should earn credit."
- "credit should be tied to changes in annotation score"; "credit is always supposed to help numericalize the decision making so
  credit and decisions by design should never fight each other".
- "regrouping AUTOMATICALLY merges and rescores annotation scorings."
- "flipping back and forth without new evidence should be net neutral."

## The mechanism

1. The head returns every candidate as found, with the identifiers of the proteins behind it (built: `function_identifiers`,
   `identifier_sources`, `leading_proteins`).
2. The root decides its function lines and, on a later commission, passes down a grouping: groups over the head's own
   candidates (each member named exactly as the head returned it).
3. The head applies the grouping in code, with no model decision, when it builds its candidate table. The held records stay as
   observed; a member's measurement rows are read under the group's key. For a structure search the rows are the hits, so a
   group's value in the test is the mean over the hits of all its members: exactly what the test would have given under one
   name. The annotation scores follow from the same arithmetic as before.
4. The grouping in force is the one of the current commission. A different grouping later gives a different table; nothing is
   undone.

## Credit

Two parts, as today, with one change.

- Admission: the entry score of each candidate when first listed, by name as found. Unchanged by a grouping. It still pays one
  function once per name; the owner knows and has accepted this for now.
- Discrimination: over the held tests, the differential of the two leading candidates. It depends on the grouping. The head's
  credit takes the HIGHEST discrimination over the groupings it has been given so far (no grouping being one of them), computed
  on the evidence it holds now.

A differential is a sum over tests of terms that are never negative and a held test's term does not change when a later test is
added, so the discrimination of a fixed grouping never falls as evidence grows. The highest over the groupings given so far is
therefore the highest it has ever been, and the head needs to keep only the groupings, not past values.

| Move | Discrimination | Earns |
|---|---|---|
| Merge spellings, so the leaders are two functions | rises | the rise |
| Back to an earlier grouping, no new evidence | already counted | nothing |
| A further grouping, no new evidence | earns only above the best so far | only an improvement |
| A new test, then the same grouping | recomputed with more evidence | its new differential |
| Split one function in two | the halves respond alike | about nothing |

So no sequence of regroupings earns more than the best grouping is worth, and the grouping that earns is the one that separates
the leaders best: the choice and the credit agree.

## What the head keeps

Applying a grouping is one unit the head owes when its commission carries a grouping it has not kept yet (taken without asking
the model, as the root takes `make_claims`). The unit keeps the grouping as a record. The head's credit reads the groupings it
holds; the records go back to the root with its other committed records and return on the next commission.

## Open

- The site and partner-contact sheets give one value per candidate, not per protein: a group's value in such a test is the mean
  of its members' values unless the sheet's own rows allow the mean over proteins. To be read from the sheets when built.
- The order of "listed before the test" for a group: that of its earliest member.
- The form of the grouping in the commission and of the grouped candidates in the return: to agree with the root's session.
- The admission part (above).
- A101 has the same candidates-by-name and the same credit rule.
