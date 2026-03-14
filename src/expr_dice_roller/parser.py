from typing import Literal

from .lexer import TT, Token, NAME_TTs, token_names
from dataclasses import dataclass

class Expr: pass

@dataclass
class BinOp(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass
class Unary(Expr):
    operator: Token
    value: Expr

@dataclass
class Grouping(Expr):
    value: Expr

@dataclass
class Number(Expr):
    value: Token

@dataclass
class Predicate(Expr):
    predicate: Token
    comp: Expr

@dataclass
class Variable(Expr):
    name: Token

@dataclass
class Function:
    name: Variable
    parameters: list[Variable]
    body: Expr

@dataclass
class FuncCall(Expr):
    function: Variable | Function
    arguments: list[Expr]


@dataclass
class Dice(Expr):
    count: Expr | None
    side: Expr | Literal['%']
    drop_high: Expr | None = None
    drop_low: Expr | None = None
    keep_high: Expr | None = None
    keep_low: Expr | None = None
    minimum: Expr | None = None
    maximum: Expr | None = None

    explode: Predicate | bool | None = None
    penetrate: Predicate | bool | None = None
    reroll: Predicate | bool | None = None
    reroll_once: bool = False

    success: Predicate | None = None
    failure: Predicate | None = None


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.position = 0

    def at_end(self) -> bool: return self.position >= len(self.tokens)

    def peek(self, lookahead: int = 0) -> Token:
        return self.tokens[self.position + lookahead] if not self.at_end() else Token(TT.ERROR, -1, "End of statement.")

    def advance(self) -> Token:
        current = self.peek()
        self.position += 1
        return current

    def match(self, *tt: TT) -> Token | None:
        if self.peek().tt in tt:
            return self.advance()
        return None

    def match_name(self) -> Token | None:
        return self.match(
            *NAME_TTs
        )

    def expect(self, *tt: TT) -> Token:
        if match := self.match(*tt):
            return match
        raise ValueError(f"Expected one of the following: {', '.join(token_names[t] for t in tt)}.")


    def binop(self, next_func, operators: list[TT]) -> Expr:
        value = next_func()
        while operator := self.match(*operators):
            right = next_func()
            value = BinOp(value, operator, right)
        return value


    def expression(self) -> Expr:
        return self.add_or_sub()

    def add_or_sub(self) -> Expr:
        return self.binop(self.mult_or_div, [TT.PLUS, TT.MINUS])

    def mult_or_div(self) -> Expr:
        return self.binop(self.unary, [TT.STAR, TT.DIV])

    def unary(self) -> Expr:
        if operator := self.match(TT.MINUS, TT.PLUS):
            return Unary(operator, self.expo())
        return self.expo()

    def expo(self) -> Expr:
        value = self.primitive()
        while token := self.match(TT.CARET):
            if isinstance(value, BinOp):
                value = BinOp(value.left, value.operator, BinOp(value.right, token, self.primitive()))
            else:
                value = BinOp(value, token, self.primitive())
        return value

    def primitive(self) -> Expr:
        n = self.atom_optional()
        if self.match(TT.D): # dice
            if self.peek().tt == TT.PERCENT:
                self.advance()
                sides = '%'
            else:
                sides = self.atom()
            dice = Dice(n, sides)
            while self.dice_modifier(dice):
                pass
            return dice
        return n

    def predicate(self) -> Predicate | None:
        if operator := self.match(TT.NEQ, TT.EQ, TT.GT, TT.GE, TT.LT, TT.LE):
            val = self.atom()
            return Predicate(operator, val)
        return None

    def dice_modifier(self, dice: Dice) -> bool:
        if self.match(TT.D, TT.DL):
            if not dice.drop_low:
                dice.drop_low = self.atom()
            else: raise ValueError(f"Dice have duplicate field: drop low.")
        elif self.match(TT.DH):
            if not dice.drop_high:
                dice.drop_high = self.atom()
            else: raise ValueError(f"Dice have duplicate field: drop high.")
        elif self.match(TT.K, TT.KH):
            if not dice.keep_high:
                dice.keep_high = self.atom()
            else: raise ValueError(f"Dice have duplicate field: keep high.")
        elif self.match(TT.KL):
            if not dice.keep_low:
                dice.keep_low = self.atom()
            else: raise ValueError(f"Dice have duplicate field: keep low.")
        elif self.match(TT.MIN):
            if not dice.minimum:
                dice.minimum = self.atom()
            else: raise ValueError(f"Dice have duplicate field: minimum.")
        elif self.match(TT.MAX):
            if not dice.maximum:
                dice.maximum = self.atom()
            else: raise ValueError(f"Dice have duplicate field: maximum.")
        elif op := self.match(TT.BANG, TT.BANG_P):
            if not dice.explode and not dice.penetrate:
                if op.tt == TT.BANG:
                    dice.explode = self.predicate() or True
                else:
                    dice.penetrate = self.predicate() or True
            else: raise ValueError(f"Dice have duplicate field: explode/penetrate.")
        elif op := self.match(TT.R, TT.RO):
            if not dice.reroll:
                if op.tt == TT.RO:
                    dice.reroll_once = True
                dice.reroll = self.predicate() or True
            else: raise ValueError(f"Dice have duplicate field: reroll.")

        elif pred := self.predicate():
            if not dice.success:
                dice.success = pred
                if self.match(TT.F):
                    dice.failure = self.predicate()
            else: raise ValueError(f"Dice have duplicate field: success.")
        else:
            return False
        return True

    def paramslist(self) -> list[Variable]:
        lst = []
        while n := self.match_name():
            lst.append(Variable(n))
            self.match(TT.COMMA)
        self.expect(TT.RPAREN)
        return lst

    def argslist(self) -> list[Expr]:
        lst = []
        while self.peek().tt != TT.RPAREN:
            expr = self.expression()
            lst.append(expr)
            self.match(TT.COMMA)
        self.expect(TT.RPAREN)

        return lst

    def atom(self) -> Expr:
        r = self.atom_optional()
        if r is None:
            self.expect(TT.NUMBER)
        return r

    def atom_optional(self) -> Expr | Function | None:
        if name := self.match_name():
            var = Variable(name)
            if self.match(TT.LPAREN):
                position = self.position
                args_list = self.argslist()
                if self.peek().tt == TT.EQ:
                    self.position = position
                    params_list = self.paramslist()
                    self.expect(TT.EQ)
                    body = self.expression()
                    return Function(var, params_list, body)

                return FuncCall(var, args_list)
            return var

        if self.match(TT.LPAREN):
            val = self.expression()
            self.expect(TT.RPAREN)
            if isinstance(val, Function) and self.match(TT.LPAREN):
                position = self.position
                args_list = self.argslist()
                if self.peek().tt == TT.EQ:
                    self.position = position
                    params_list = self.paramslist()
                    self.expect(TT.EQ)
                    body = self.expression()
                    return Function(val.name, params_list, body)
                return FuncCall(val, args_list)
            return Grouping(val)

        if n := self.match(TT.NUMBER):
            return Number(n)

        return None
