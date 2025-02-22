from lark import Lark, Transformer

# Define the grammar as a raw string

# CONSTANT: /[A-Z_]+[0-9]*[A-Z_]*/

grammar = """
start: expr

?expr: and_expr
     | or_expr
     | not_expr
     | assign_expr

and_expr: "and" "(" args ")"
or_expr: "or" "(" args ")"
not_expr: "not" "(" expr ")"
assign_expr: NAME "=" ( list_value | value)

args: (expr ("," expr)*)?

list_value: "[" (value ("," value)*)? "]"

value: NUMBER | STRING | STRING_SQ | BOOLEAN

NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
NUMBER: /[0-9]+/
STRING: /"[^"]*"/
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

    def STRING(self, token):
        return token.value

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
