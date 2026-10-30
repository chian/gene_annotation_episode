# A105 evidence-axis insert — target-material correction, proposal for review

This revision supersedes the target wording in prompt_insert.md. The earlier
proposal remains preserved. Only target identification is being revised here;
the scoring-sheet and reader examples are unchanged.

## User's correction, verbatim

> so annotation text relies too much on a name. what if we have a file? what if we have a sequence? what if we have snippets. this first line of the investigation prompt needs to be more flexible. most novel things will not have identifiers that make sense to anyone by any search. it will be only internal to the team. think of how this will be used and make this make better sene. I'm going to move on to the other points in order as well. Do this first.

## Revised text inserted into TASK

Determine whether experimental molecular activity supports **{candidate annotation being investigated}** for **the gene or protein represented by the supplied material**. The target may be supplied as a sequence, a specified record or region in a file, or snippets. Use that material and its stated boundaries to establish what is being annotated. An internal name is a label; a searchable public identifier is not required. Preserve any limitations of partial sequences or snippets.

Examine what substrate became which product, what was transported, or what bound, using published findings or analysis of actual experimental data.

Retain the assayed subject/preparation, molecular endpoint, native quantities/units, controls, conditions and source experiment/dataset. Distinguish direct molecular measurements from proxies, including proteomic abundance or association. A close homolog's measured activity is relevant: keep its measurement separate from the correspondence and limitations connecting it to **the supplied target**. Preserve negative results, uncertainty and untested conditions. Binding, conversion, transport and physiological role remain distinct conclusions.

## Target material supplied with the assignment

The parent supplies the actual material or access to it, not merely an assumed
public name. Render the applicable target description in TASK:

- Inline sequence: the supplied sequence and its stated molecule type; preserve
  whether it is complete or partial and any supplied biological context.
- File: the accessible file and the selected record or region when needed to
  distinguish the assigned target. A filename alone does not select one target
  out of a multi-record file.
- Snippets: the actual supplied excerpts/fragments and their stated relation to
  the target, including known boundaries and limitations. Do not silently join
  fragments or treat a description as a complete sequence.

Use only provided or established biological context. No organism, public
accession, complete sequence, homolog correspondence or file access is assumed
merely because a label is present. If the supplied material does not distinguish
the assigned target, preserve that specific ambiguity rather than choosing a
different target.

These are ways to identify the same assigned object, not new episode types,
mandatory investigation steps or new evidence-axis scoring fields. This file
is review text; it does not establish a production renderer change.

## Subsequent correction

The user rejected the assumption that a candidate annotation already exists.
prompt_insert_003.md is the current review proposal. It starts from supplied
material and seeks evidence from which possible functions can emerge. This
earlier revision is retained as history.
