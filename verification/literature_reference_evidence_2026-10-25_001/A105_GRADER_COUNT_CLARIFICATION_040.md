# Count clarification after the user's experimental-grader questions

There is one A105 axis sheet,still incomplete. Multiple experimental component
graders and supporting input functions populate its numerical meanings. Ten
axes remain; neither experiment types nor selected tools add new axes.

Current grouping by purpose:

| Six substantive component families | Selected operations |
| --- | --- |
| Source rate contrasts | literature.rate.populate; literature.rate.source.populate |
| Corrected source activity | literature.assay.populate |
| Relative signals/abundance | literature.ratio.populate |
| Binding parameters and conditional binding models | literature.binding.populate; literature.binding.model.populate |
| Conditional transport response | literature.transport.response.populate |
| Experimental partner omission/add-back,also supporting later partner knowledge | literature.partner.populate; literature.partner.source.populate |

Those are nine operations serving six finite component families. They are not
six universal complete experimental graders. Some compute descriptive quantities
or correction operands; some statistical cells explicitly remain unknown without
supported uncertainty/model inputs. Scientific verification must be reported per
supported input/design and actual source example.

Two supporting calculator families supply amount comparisons and optical
conversion. Two additional extraction routes handle single reported quantities
and figure measurements. Together these account for13 A105-relevant/shared
experimental operations. The remaining four of17 operations concern
perturbation,structure,reaction and organism/sample context.17 is not the number
of A105 graders or sheets.

The earlier estimate8–12 reusable component-grader families is a provisional
planning estimate,not a fixed endpoint. The number of individual method readers
is not yet established. Case-based coverage must determine what is needed;
finishing a chosen number does not satisfy the goal. In particular the source
kinetic-parameter comparison identified in case038 is not implemented by the
existing raw-rate or reported-percent paths.

The current user clarification in LITERATURE_GRADER_SELECTION_TARGET_040.md
defines the intended consumer: a literature investigation identifies relevant
experimental results and selects applicable graders to populate the appropriate
sheet components. That routing link is not an implementation priority now.
