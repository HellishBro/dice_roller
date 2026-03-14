from expr_dice_roller import *

env = Environment().serialize()

while True:
    inp = input("> ")
    try:
        print(format_expression(inp))
        e = Environment.deserialize(Evaluator(), env)
        res = evaluate(inp, e, True)
        env = res.environment.serialize()
        print(res.representation, "=", res.value)
    except ValueError as e:
        print(e)