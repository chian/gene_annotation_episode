# A105 evidence-axis insert — discovery from supplied material

Proposal for review, 2026-10-23. Supersedes the prompt in prompt_insert_002.md;
earlier proposals remain preserved. No production renderer change is claimed.

## User's correction, verbatim

> Back to your comment on point 1: The new prompt has a new problem. It assumed that there is a candidate annotation already? What if you don't know what it is at all? That basically makes no sense to start with hey, test this hypothesis. The whole point is to gather evidence for what something is not to start with a suggestions. This
> Determine whether experimental molecular activity supports {candidate annotation being investigated} for the gene or protein represented by the supplied material. --> really makes no sense. The point is you don't have a candidate annotation being investigated yet. You have a sequence

## Revised text inserted into TASK

Find and evaluate experimental evidence to determine what molecular activities the supplied gene or protein may perform. Start from the supplied sequence, specified file record or region, or snippets. A candidate annotation or searchable public name is not required; possible functions should emerge from the evidence.

Examine measurements of substrate conversion, transport or binding from published findings or experimental datasets, including measurements on relevant homologs. Distinguish what was measured on the actual assayed subject from what can be inferred about the supplied target.

Retain the assayed subject/preparation, molecular endpoint, native quantities/units, controls, conditions and source experiment/dataset. Distinguish direct molecular measurements from proxies, including proteomic abundance or association. For homolog evidence, retain the correspondence and limitations connecting the measured activity to the supplied target. Preserve negative results, uncertainty, and the boundaries of partial sequences or snippets. Binding, conversion, transport and physiological role remain distinct conclusions.

## Construction meaning

The parent supplies the scoped assignment and available target material. It
need not supply a function hypothesis. Later findings can introduce candidate
functions for comparison or revision; an initial candidate is not a required
construction field for this prompt. Existing candidate information, when
actually supplied, can inform the assignment without making candidate testing
the default starting task.

The earlier file/record/region and partial-material handling remains applicable.
This correction adds no mandatory itinerary, new episode type, stopping rule,
scoring policy or new reader implementation.
