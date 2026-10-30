# Addendum: signed contributions and the annotation interface remain distinct

2026-10-23. This additive clarification applies to
`CONTRIBUTION_PROPOSAL_001.md`, especially its phrase “bounded contribution.”
It leaves that proposal and the checked arithmetic unchanged.

The proposed profile contrast `S` can be negative. Its proposed normalized
version `B=tanh(S/2)` ranges from `-1` to `1`. The existing annotation hypervolume
expects nonnegative support coordinates. **B is therefore not a directly wired
A105 coordinate.** The research proposal does not establish that interface.

The three outputs must stay separate:

| Quantity | Positive paired-preference example | Opposite statement about the same data | Meaning |
|---|---:|---:|---|
| Native mean rate difference | `+1.5 micromolar/minute` | `-1.5 micromolar/minute` | Observed magnitude and direction |
| Directional profile log likelihood S | `+8.736786139 nats` | `-8.736786139 nats` | Separation of the two best directional fits |
| Proposed normalized value B | `+0.999678913` | `-0.999678913` | Normalized likelihood-fit difference; not a probability |

The annotation-interface choice is how compatible supporting and opposing
evidence about a particular function should determine the nonnegative A105
coordinate expected by the retained annotation formula. It must also define
what a measured null, an unknown value, absent evidence and an unresolved
transfer relationship mean at that boundary. This is not settled by putting
signed data through a convenient transform.

No clamp of negative values to zero, `0.5` neutral baseline, discarded opposing
evidence, silently altered hypervolume, or replacement global scoring formula
is adopted here. Nor does this document invent an independence assumption to
combine activity, specificity, target correspondence and physiological role.
The existing nonnegative coordinate's meaning and any prospective change need
explicit user review and the separate W05 consumer work. Native effects and
signed contributions remain useful numerical sheet outputs while that choice
is unresolved; they must not be presented as completed axis wiring.

The normalized value B can saturate despite a tiny effect. For the exact
synthetic values `log(ratio)=0.001`, `SE=0.00001`, known normal variance gives
`z=100`, `S=5000`, and mathematically `B<1` but indistinguishable from one at
ordinary floating-point precision. The ratio is only `1.0010005001667084`.
This strongly separates the signs of that tiny contrast; it does not create a
large specificity effect or establish biological importance. A stored rounded
`B=1.0` must not be interpreted as certainty. Retaining S, effect magnitude,
native uncertainty and model scope prevents the bounded representation from
erasing that distinction.

The main proposal's compound-claim likelihood example is a mathematical option
for an explicitly defined inference. It is not an authorization to redefine
the global annotation score or a mandatory experimental acceptance rule.

