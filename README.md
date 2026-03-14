# Expression Dice Roller

Install from PyPI: `pip install expr_dice_roller`

Quick command-line dice roller set up:
```python
from expr_dice_roller import format_expression, evaluate

env = None

while True:
    inp = input("> ")
    try:
        print(format_expression(inp))
        res = evaluate(inp, env, True)
        env = res.environment
        print(res.representation, "=", res.value)
    except ValueError as e:
        print(e)
```

It is possible to serialize an expression by using `format_expression()`, which can then be used in `evaluate()`.

## Language Specifications
Arithmetic words with the operators `+`, `-`, `*`, `/`, and `^`. Unary operators `-` and `+` are supported.

The language closely mirrors [RPG Dice Roller](https://dice-roller.github.io/documentation/guide/notation/)'s notations, with a few unimplemented or extra parts:
- Fudge dice is not yet implemented.
- Critical success / failures are not yet implemented.
- Grouping rolls are not yet implemented.
- New features includes variables and functions.

### Variables
Variables have a name comprised of any string of characters that are not part of the language itself. There are no built-in variables except for the `_` variable when `evaluate()` is called with `assign_last_eval=True`.

The `_` variable, if provided, will point to the value of the last successful eval.

### Functions
Functions are declared like so: `f(x, y, z, ...) = expression`. They can be immediately called if surrounded by brackets.

Example functions:
- `f(x) = 2 * x` - doubles the input.
- `dice(count, sides) = (count)d(sides)` - rolls `count` dice each with `sides` sides.
- `dice(4, 3)` - calls the `dice` function, effectively rolling a `4d3`.
- `(g(x, y)=f(x)-f(y))(2, 3)` - immediately invoked function that calls another function.

Extraneous arguments beyond the arity of the function will be voided. Similarly, missing arguments below the arity of the function will be turned to `0`.

Functions cannot be arbitrarily chained yet; currently, functions are parsed as special exceptions to certain rules.