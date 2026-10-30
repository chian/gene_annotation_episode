# Drawing episode trees

**Every Episode is a decision point that iterates, that's it.**

Draw the recurring question each episode owns. Its decisions use earlier
outcomes and can revise the approach. Nesting shows the scope of those decision
points; runtime sequence emerges from their decisions.

The unit being composed is an intelligence carrying out a problem-solving
process. The information library fills the common episode template to help
construct a child's decision problem and limit its alternatives on each turn.
Named nodes describe those decisions, not a requirement to handwrite a separate
episode class for every process. See EPISODE_STRUCTURE.md for this design and
the distinction from the currently implemented manual library and role bindings.

The user's accepted example:

```text
Scientific parent: what uncertainty matters next?
└─ Investigation: how can this specific question be resolved?
   └─ Strategy: which search approach is productive?
      └─ Search: which returned sources deserve examination?
         └─ Page: where and how should this source be examined?
            ├─ Table investigation
            ├─ Ordered reading
            └─ Targeted passage investigation
```

Keep diagrams concise and targeted to iteration. The leaves above also denote
iterative decision points within the page investigation, not single operations.
Do not turn a tree into a catalog of everything possible, subject departments,
task lists, or a prescribed start-to-end workflow. When asked for an episode-only
diagram, omit action, tool, and A/T nodes.

Before retaining a node, identify the decision it revisits and how outcomes can
change its next choice. Renaming an operation or catalog does not make it an
episode. Discard mistaken diagram assumptions explicitly; do not explain them
away, rephrase them into designs, or pass them to another assistant as accepted
requirements. Recheck the user's definition and accepted example after revisions.

For questions about the current implementation, draw only structure supported by
the code. Inspect `runtime.Workflow.grain_names`, `Workflow.__init__`, `selected`,
`action_schema`, and `HomologyEpisodes.ROLES` as relevant. State what those paths
establish and leave unsupported structure out. The accepted example above is not
evidence of implementation. Keep any requested proposal separate from the actual
tree; do not imply user approval or surround an implementation answer with lists
of unimplemented features.
