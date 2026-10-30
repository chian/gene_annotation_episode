# Amount interpretation TASK insertion: proposal027

This proposed recurring instruction concerns one aspect of the existing
literature investigation. It does not replace its assignment or return form.
The sheet and deterministic implementation stay separate.

> Determine which reported molecular amounts describe the preparations or arms
> relevant to the assigned experiment. Identify the actual molecule, construct,
> preparation or stock, measurement method, reported amount basis and condition
> for each quantity before nominating numerical and unit spans. Preserve unknown
> meanings rather than completing them from a nearby protein name. Distinguish
> mass concentration from molar concentration, estimated target protein from
> total protein, and nominal recipe amount from measured active concentration.
>
> For estimates of target and total protein in one stock, identify which estimate
> belongs in the numerator and which in the denominator, and retain the methods
> and source passages establishing that they describe the same stock. Their
> comparison can describe a change of mass denominator under that relationship;
> it does not measure active fraction, contaminant activity, recovery or purity.
> Different estimates can yield a target/total ratio above one. Preserve that
> result and its limitations. Do not turn it into a probability or repair it.
>
> For nominal molar amounts in different experimental arms, identify both actual
> molecules and preparations, the experiment connecting those arms and the
> deliberately changed variable. Their amount difference can qualify how
> comparable the arms are outside that intended change. It does not establish
> an amount-response correction, equal active sites or isolation of the measured
> effect. Replacement across vessels does not establish the purity of either
> preparation. Keep experimental comparability separate from effect isolation.
>
> Nominate exact original number and unit spans; deterministic operations parse,
> validate, convert supported units and perform arithmetic. Preserve inequalities
> and approximation, including prose that qualifies an estimate without sitting
> immediately next to its number. Do not infer a molecular weight, reaction
> volume, source denominator or stock relationship from matching units. A
> missing comparison relationship does not erase an individually reported value.
>
> Preserve reported uncertainty and physical observation identity. An approximate
> estimate is not a standard error, and SD, SEM, confidence intervals and untyped
> spreads retain their own meanings. Repeated representations and shared
> observations are not independent measurements. Supply a retained covariance
> source only when its actual quantities, units and ordered owners apply; missing
> covariance stays unknown. Do not compose numerical covariance or assume zero
> dependence to complete a requested cell.
>
> Before any later use of a mass-denominator factor, establish that the saved
> rate uses this actual stock and total protein mass as its denominator. An
> already target-normalized rate must not receive the conversion again. The
> present amount operation retains this conditional relationship without
> inventing a rate or an activity correction. Return only the parent's requested
> typed information, with these scientific qualifications. Target correspondence
> and combined annotation credit remain separate work.

## Decision/information trace

The episode decides which comparison exists, which source quantities have its
meanings and what further reading could resolve a missing relationship. Source
selectors and constrained scientific meanings are selected-operation inputs;
the reader binds exact bytes and units, and the calculator fills numerical
cells. The ordinary selected action owns its observation. Saving, calculating
and rendering add no internal actions or synthetic yield observations.

TASK repeats the instructions above. STEERING shows only selected result cells,
actual numerator/denominator meanings, nominal/estimate/approximate status,
necessary uncertainty and unavailable reasons. Host source hashes, physical
keys, covariance owner keys and implementation identities remain outside the
model-facing text. Existing typed returns preserve validated scientific
meanings; no report-composition model call is added.
