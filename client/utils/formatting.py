"""Formatting utilities."""

from client import exceptions
import textwrap

#############
# Whtespace #
#############

def dedent(text):
    """Dedents a string of text.

    Leading whitespace that is common to all lines in the string is
    removed. Any leading newlines and trailing whitespace is also
    removed.
    """
    return textwrap.dedent(text).lstrip('\n').rstrip()

def indent(text, indentation):
    """Indents a string of text with the given string of indentation.

    PARAMETERS:
    text        -- str
    indentation -- str; prefix of indentation to add to the front of
                   every new line.

    RETURNS:
    str; the newly indented string.
    """
    return '\n'.join([indentation + line for line in text.splitlines()])

############
# Printing #
############

def underline(text, line='='):
    """Prints an underlined version of the given line with the
    specified underline style.

    PARAMETERS:
    line  -- str
    under -- str; a one-character string that specifies the underline
             style
    """
    print(text + '\n' + line * len(text))

def print_title(text):
    """Prints the given text as a "title" to standard output, in the
    following format:

    ###########
    Sample Text
    ###########
    """
    print('#'* len(text))
    print(text)
    print('#'* len(text))
    print()

#################
# Serialization #
#################

def prettyjson(json, indentation='  '):
    """Formats a Python-object into a string in a JSON like way, but
    uses triple quotes for multiline strings.

    PARAMETERS:
    json        -- Python object that is serializable into json.
    indentation -- str; represents one level of indentation

    NOTES:
    All multiline strings are treated as raw strings.

    RETURNS:
    str; the formatted json-like string.
    """
    if isinstance(json, int) or isinstance(json, float):
        return str(json)
    elif isinstance(json, str):
        if '\n' in json:
            return 'r"""\n' + dedent(json) + '\n"""'
        return repr(json)
    elif isinstance(json, list):
        lst = [indent(prettyjson(el, indentation), indentation) for el in json]
        return '[\n' + ',\n'.join(lst) + '\n]'
    elif isinstance(json, dict):
        pairs = []
        for k, v in sorted(json.items()):
            k = prettyjson(k, indentation)
            v = prettyjson(v, indentation)
            pairs.append(indent(k + ': ' + v, indentation))
        return '{\n' + ',\n'.join(pairs) + '\n}'
    else:
        raise exceptions.DeserializeError('Invalid json type: {}'.format(json))

