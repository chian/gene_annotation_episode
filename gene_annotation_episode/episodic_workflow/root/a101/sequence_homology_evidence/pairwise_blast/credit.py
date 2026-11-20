"""Credit: only what is gained (owner decision D17). The episode establishes one thing, the correspondence of the
query with the subject, and it is established when a grading of the pairwise sheet for the job's own two operands is
saved. Then the commission's information unit is earned, once. The launch, a check, a fetch, a refused grading and a
repeat of a grading already saved earn nothing: a repeat adds no knowledge, and the task offers the grading only
while none is saved. The summary reads the saved gradings from the records the episode holds, so the credit is of a
record in custody, not of what a tool said."""


def credit(summary, records):
    return summary['information_unit'] if summary['execution_completed'] else 0.0
