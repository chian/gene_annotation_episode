# Additive numerical display correction

The exact illustrative same-curve response for St10,Sr40,Km16.5 is113/212,
whose nearest binary64 display is **0.5330188679245284**. Interfaces001 and the
parent review printed0.5330188679245283 from rounded intermediate arithmetic.
The implemented calculator uses exact rational intermediate arithmetic and
returns0.5330188679245284. This corrects one last display digit; it does not
change the scientific requirement for a shared applicable kinetic curve or
make the actual cross-system correction available.
