"""The one validator of the controlled finding features that every A101 feature reader produces.

A feature reader names its features in a table ``name -> rule`` and calls ``validated`` on what it read from a saved
sheet. A rule is a tuple whose first item names the kind of value:

* ``('number', low, high)``: a finite number in the closed range;
* ``('count',)``: a non-negative integer;
* ``('choice', options)``: one of the options;
* ``('boolean',)``: a boolean;
* ``('text',)``: a non-empty string of at most 200 characters (an identifier or a name from a controlled list);
* ``('refs',)``: a non-empty list of record references;
* ``('ref',)``: a list of exactly one record reference.

A rule is optional when its last item is ``'optional'`` (``('number', 0, 1, 'optional')``) or when it is wrapped
(``('optional', rule)``): an optional feature is absent when the sheet does not give it, and nothing is defaulted.
A feature that is present must satisfy its rule, a feature the table does not name is an error, and a missing
required feature is an error. Nothing here reads a sheet."""
import math


def optional(rule):
    return rule[0] == 'optional' or rule[-1] == 'optional'


def valid(value, rule):
    kind = rule[0]
    if kind == 'optional':
        return valid(value, rule[1])
    if kind == 'number':
        return type(value) in (int, float) and math.isfinite(value) and rule[1] <= value <= rule[2]
    if kind == 'count':
        return type(value) is int and value >= 0
    if kind == 'choice':
        return value in rule[1]
    if kind == 'boolean':
        return type(value) is bool
    if kind == 'text':
        return type(value) is str and 0 < len(value) <= 200
    if kind == 'refs':
        return type(value) is list and bool(value) and all(type(ref) is str for ref in value)
    if kind == 'ref':
        return type(value) is list and len(value) == 1 and type(value[0]) is str
    raise ValueError('feature_rule_kind_unknown:' + repr(kind))


def validated(features, rules, what):
    """``features`` against ``rules``; ``what`` prefixes the error codes (``<what>_features_mismatch`` and
    ``<what>_feature_invalid:<name>``). Returns ``features``."""
    required = {name for name, rule in rules.items() if not optional(rule)}
    if not required <= set(features) <= set(rules):
        raise ValueError(what + '_features_mismatch')
    for name, value in features.items():
        if not valid(value, rules[name]):
            raise ValueError(what + '_feature_invalid:' + name)
    return features


__all__ = ['optional', 'valid', 'validated']
