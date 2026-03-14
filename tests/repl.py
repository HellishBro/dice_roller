from expr_dice_roller import *

env = Environment().serialize()

while True:
    inp = input("> ")
    try:
        print(format_expression(inp))
        res = evaluate(inp, Environment.deserialize(env), True)
        env = res.environment.serialize()
        print(res.representation, "=", res.value)
    except ValueError as e:
        print(e)