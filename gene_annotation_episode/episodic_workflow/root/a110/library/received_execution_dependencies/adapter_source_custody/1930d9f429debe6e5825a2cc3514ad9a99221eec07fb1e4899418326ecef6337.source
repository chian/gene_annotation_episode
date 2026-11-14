"""Inert JSON lexical tokens and bounded array rows, shared by native formats."""

class _Numeric(str):
    pass


class _Pairs(list):
    pass


def _valid_text(value):
    if type(value) is not str:
        return False
    try:
        value.encode('utf-8', errors='strict')
    except UnicodeError:
        return False
    return True


def _rows(text):
    """Split only at structurally bounded top-level array commas.

    A malformed bounded row does not erase an intact sibling. An unfinished
    string/container does not permit guessing where the next row begins.
    """
    position = 0
    while position < len(text) and text[position].isspace(): position += 1
    if position == len(text) or text[position] != '[':
        return [], False
    position += 1; start = position; stack = []; quoted = False; escaped = False; result = []
    while position < len(text):
        char = text[position]
        if quoted:
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == '"': quoted = False
        elif char == '"': quoted = True
        elif char in '{[': stack.append(char)
        elif char in '}]':
            if char == ']' and not stack:
                fragment = text[start:position]
                if fragment.strip(): result.append((start, position, fragment, True))
                elif result: result.append((start, position, fragment, False))  # trailing comma
                return result, not text[position + 1:].strip()
            if not stack or (stack.pop(), char) not in (('{', '}'), ('[', ']')):
                return result + [(start, position + 1, text[start:position + 1], False)], False
        elif char == ',' and not stack:
            result.append((start, position, text[start:position], True)); start = position + 1
        position += 1
    if text[start:].strip(): result.append((start, len(text), text[start:], False))
    return result, False


