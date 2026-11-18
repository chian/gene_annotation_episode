"""Private A102 literature_targeted goal."""
from __future__ import annotations

class SourceGoal:

    def instructions(self, context):
        self._role(context.role)
        return 'Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.' + "\nThis is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted child forms inform later choices; no child order, reading quota or complete-document requirement is prescribed. A one-off search/read is an ordinary tool. A supplied reading selector is context, not an automatically executed action. Preserve the source's actual subject, experimental conditions, representation, version and UTF-8 byte anchors. Distinguish source claims from their applicability to the fixed target. Negative findings and qualifications can advance the investigation. Commit interpretations with the common reasoning action and update only the parent's declared typed form in that same work call. Navigation, byte coverage and repeated reading earn no scientific credit by themselves. The commissioned task's own yield settings guide continuation."
