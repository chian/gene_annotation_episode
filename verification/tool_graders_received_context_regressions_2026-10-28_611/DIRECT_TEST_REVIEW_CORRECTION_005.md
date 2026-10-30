# Review correction: selected reasoning instead of a context inspection

Root reviewed the passing check062 fixture and requested that its single child
action be reasoning, so this regression does not endorse a context lookup as an
own observation. Preserve check062 and its saved-evidence collector results.

The suggested completely empty typed commit is not legal: the complete
`DecisionSource.apply_response` implementation at runtime.py:1567–1571 rejects
an all-empty required-collection payload as `empty_reasoning_commit`. This
method is identical in check060, check062 and the current source. Do not bypass
or change that production behavior for a test.

Replace only the child callback and selected action with a legal nonempty typed
reasoning commit. It records an unresolved biological-role hypothesis using the
supplied target scope, with no assessment, observation, source, annotation or
finding. Its payload is constructed from the supplied scope, never from the
unreceived stored finding or its identifier. Such a hypothesis contributes zero
under the existing child ScientificFindingProgress projector.

Keep all passing custom-callable, received-view, empty initial-known-list,
stored-finding preservation, parent-return and one-observation-per-episode
assertions. Add exact assertions for one reasoning commit and zero tool
operations. Rename `read` to `reason`. No scoring or runtime changes.

Run only the revised direct regression through the existing packet529 bounded
runner, using check005 dependencies and the unique
`check065_received_context_direct_final` attempt. Do not rerun the saved-row
collector or any native scientific analysis. Inspect frozen source hashes and
the final execution receipt before reporting this revised fixture as verified.
