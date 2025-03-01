from shlex import quote

from lark import Lark, Transformer

# Define the grammar as a raw string

# CONSTANT: /[A-Z_]+[0-9]*[A-Z_]*/

from datetime import datetime


def iso_to_datetime(iso_string):
    """
    Convert ISO format string to datetime object.
    Handles both date-only (YYYY-MM-DD) and datetime (YYYY-MM-DDTHH:MM:SS) formats.
    """
    try:
        # Try parsing as a full datetime with timezone info
        return datetime.fromisoformat(iso_string)
    except ValueError:
        try:
            # Try parsing as date-only format
            return datetime.strptime(iso_string, "%Y-%m-%d")
        except ValueError:
            # Handle other ISO 8601 formats that might not be directly supported by fromisoformat
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO format with milliseconds and Z
                "%Y-%m-%dT%H:%M:%SZ",  # ISO format with Z
                "%Y-%m-%dT%H:%M:%S",  # ISO format without timezone
                "%Y-%m-%d %H:%M:%S",  # Date and time separated by space
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(iso_string, fmt)
                except ValueError:
                    continue

            raise ValueError(f"Could not parse ISO string: {iso_string}")

grammar =r"""
start: expr

?expr: and_expr
     | or_expr
     | not_expr
     | assign_expr
     | bracket_expr
     | q_expr

and_expr: "and" "(" args ")"
or_expr: "or" "(" args ")"
not_expr: "not" "(" expr ")"
bracket_expr: "(" expr ")"
q_expr: "q" "(" expr ")"
assign_expr: NAME "=" ( list_value | value)

args: (expr ("," expr)*)?

list_value: "[" (value ("," value)*)? "]"

value: STRING_DQ | STRING_SQ  | BOOLEAN | NUMBER 

NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
NUMBER: /[0-9]+/
STRING_DQ: /"[^"]*"/
STRING_SQ: /'[^']*'/
BOOLEAN: "True" | "False"

%import common.WS
%ignore WS
"""

parser = Lark(grammar, parser='lalr')


class QTransformer(Transformer):
    def and_expr(self, items):
        args = items[0]
        return f"Q({args},join_type='AND')"

    def bracket_expr(self, items):
        args = items[0]
        return f"Q({args})"

    def q_expr(self, items):
        args = items[0]
        return f"Q({args})"

    def or_expr(self, items):
        args = items[0]
        return f"Q({args},join_type='OR')"

    def not_expr(self, items):
        expr = items[0]
        return f"~Q({expr})"

    def assign_expr(self, items):
        name = items[0]
        value = items[1]
        return f"Q({name}={value})"

    def args(self, items):
        if items:
            return ",".join(items)
        return ""

    def list_value(self, items):
        return f"[{','.join(items)}]"

    def value(self, items):
        return items[0]

    def NAME(self, token):
        return token.value



    def NUMBER(self, token):
        return token.value

    def _str(self, value, quote=''):
        try:
            if value[0]==value[-1] and value [0] in ('"',"'"):
                value=value[1:-1]

            t = iso_to_datetime(value)

            return f'datetime.datetime({t.year}, {t.month}, {t.day}, {t.hour}, {t.minute}, {t.second})'

        except Exception as e:
            pass

        return f'{quote}{value}{quote}'


    def STRING_DQ(self, token):
        return self._str(token.value, quote='"')

    def STRING_SQ(self, token):
        return self._str(token.value, quote="'")

    def BOOLEAN(self, token):
        return token.value


def transform_filter_param_to_Q(s):
    if not hasattr(transform_filter_param_to_Q, 'parser'):
        transform_filter_param_to_Q.parser = Lark(grammar, parser='lalr')

    tree = transform_filter_param_to_Q.parser.parse(s)
    transformer = QTransformer()
    try:
        r = transformer.transform(tree)
    except Exception as e:
        raise e

    res = r.children[0]
    return res

if __name__=='__main__':
    print(transform_filter_param_to_Q('or(and(a=1,b=2),c=3)'))
    print(transform_filter_param_to_Q('(a=1)'))
    print(transform_filter_param_to_Q('(level="info")'))

    print(transform_filter_param_to_Q('and(q(a=1),q(b=2))'))
    print(transform_filter_param_to_Q('and(a=1,b=2)'))

    print(transform_filter_param_to_Q('and(created__gt="2025-05-22T10:00:00",b=2)'))
    print(transform_filter_param_to_Q('and(created__gt="2025-05-22",b=2)'))
    print(transform_filter_param_to_Q('and(created__gt="2025-05-22",b=2)'))
    #
    print(transform_filter_param_to_Q('q(and(q(level="info"),level="error"))'))