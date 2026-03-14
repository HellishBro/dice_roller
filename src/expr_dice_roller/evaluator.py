from __future__ import annotations
from .lexer import TT, Lexer
from .parser import Expr, BinOp, Unary, Number, Dice, Grouping, Predicate, FuncCall, Variable, Function, Parser
from .dice_roller import Dice as DDice, DiceRoller, Predicate as DPredicate
import json
import gzip

class IEvaluator:
    def __init__(self, environment=None):
        self.environment = environment or Environment()

    def enter(self):
        self.environment = self.environment.enter()

    def exit(self):
        self.environment = self.environment.exit()

    def visit(self, node):
        return getattr(self, "visit_" + node.__class__.__name__)(node)

class EvalFunc:
    def __init__(self, parameters: list[str], body: Expr, definition: Function):
        self.parameters = parameters
        self.body = body
        self.definition = definition

    def call(self, evaluator: IEvaluator, arguments: list[float]) -> float:
        evaluator.enter()
        for param, arg in zip(self.parameters, arguments):
            evaluator.environment.assign(param, arg)
        _, val = evaluator.visit(self.body)
        evaluator.exit()
        return val

    def __str__(self) -> str:
        return Printer().visit_Function(self.definition)


class Environment:
    def __init__(self):
        self.parent: Environment | None = None
        self.variables: dict[str, float | EvalFunc] = {}

    def enter(self):
        new_env = Environment()
        new_env.parent = self
        return new_env

    def get(self, name: str) -> float | EvalFunc:
        if self.parent is None:
            return self.variables.get(name, 0)
        return self.variables.get(name, self.parent.get(name))

    def assign(self, name: str, value: float | EvalFunc):
        self.variables[name] = value

    def exit(self):
        p = self.parent
        self.parent = None
        return p

    def serialize(self) -> bytes:
        return gzip.compress(json.dumps({
            "parent": self.parent.serialize() if self.parent else None,
            "variables": {
                k: (v if isinstance(v, (float, int)) else Printer().visit(v))
                for k, v in self.variables.items()
            }
        }).encode("utf-8"))

    @classmethod
    def deserialize(cls, data: bytes) -> Environment:
        parsed = json.loads(gzip.decompress(data).decode("utf-8"))
        env = Environment()
        if parsed.get("parent"):
            env.parent = Environment.deserialize(parsed.get("parent"))
        for k, v in parsed.get("variables", {}).items():
            env.variables[k] = v if isinstance(v, (float, int)) else Parser(Lexer(v).lex()).expression()
        return env


ReprValue = tuple[str, float | EvalFunc]
class Evaluator(IEvaluator):
    def __init__(self, environment=None):
        super().__init__(environment)
        self.function_depth = 0

    def visit_BinOp(self, node: BinOp) -> ReprValue:
        left_repr, left_val = self.visit(node.left)
        right_repr, right_val = self.visit(node.right)
        left_val = self._float(left_val)
        right_val = self._float(right_val)
        operator = node.operator
        op = ""
        res = 0
        if operator.tt == TT.PLUS:
            res = left_val + right_val
            op = "+"
        elif operator.tt == TT.MINUS:
            res = left_val - right_val
            op = "-"
        elif operator.tt == TT.STAR:
            res = left_val * right_val
            op = "*"
        elif operator.tt == TT.DIV:
            if right_val == 0:
                res = 0
            else:
                res = left_val / right_val
            op = "/"
        elif operator.tt == TT.CARET:
            res = left_val ** right_val
            if isinstance(res, complex):
                res = 0
            op = "^"
        return f"{left_repr} {op} {right_repr}", res

    def visit_Unary(self, node: Unary) -> ReprValue:
        val_repr, val = self.visit(node.value)
        val = self._float(val)
        operator = node.operator
        op = ""
        res = 0
        if operator.tt == TT.PLUS:
            res = abs(val)
            op = "+"
        elif operator.tt == TT.MINUS:
            res = -val
            op = "-"
        return f"{op}{val_repr}", res

    def visit_Number(self, node: Number) -> ReprValue:
        d = self._float(node.value.data)
        return f"{d:g}", d

    def visit_Grouping(self, node: Grouping) -> ReprValue:
        rep, res = self.visit(node.value)
        return f"({rep})", res

    def visit_Predicate(self, node: Predicate) -> DPredicate:
        return DPredicate({
            TT.NEQ: "<>",
            TT.EQ: "=",
            TT.GT: ">",
            TT.LT: "<",
            TT.GE: ">=",
            TT.LE: "<="
        }[node.predicate.tt], self._float(self.visit(node.comp)[1]))

    def visit_Function(self, node: Function) -> ReprValue:
        func = EvalFunc([param.name.data for param in node.parameters], node.body, node)
        self.environment.assign(node.name.name.data, func)
        return self.visit(node.name)

    def visit_Variable(self, node: Variable) -> ReprValue:
        return node.name.data, self.environment.get(node.name.data)

    def visit_FuncCall(self, node: FuncCall) -> ReprValue:
        rep, func = self.visit(node.function)
        rep_args = [self.visit(arg) for arg in node.arguments]
        reps = [rep_arg[0] for rep_arg in rep_args]
        args = [rep_arg[1] for rep_arg in rep_args]
        rep += "(" + ", ".join(reps) + ")"
        if not hasattr(func, "call"):
            n = node.function.name.name.data if isinstance(node.function.name, Variable) else node.function.name.data
            raise ValueError(f"{n} is not a defined function.")

        if self.function_depth > 100:
            raise ValueError(f"Max function depth limit reached.")
        self.function_depth += 1
        value = func.call(self, args)
        self.function_depth -= 1
        return rep, value

    @staticmethod
    def _float(value) -> float:
        if isinstance(value, (int, float, str)):
            return float(value)
        raise ValueError(f"{value} cannot be interpreted as a number.")

    @staticmethod
    def _int(value) -> int | None:
        if isinstance(value, (int, float)):
            if value.is_integer():
                return int(value)
            else:
                raise ValueError(f"{value} is not an integer.")
        elif value is None: return None
        raise ValueError("Functions cannot be interpreted as an integer.")

    def visit_Dice(self, node: Dice) -> ReprValue:
        count = self.visit(node.count)[1] if node.count else None
        sides = self.visit(node.side)[1] if node.side != "%" else 100
        drop_high = self.visit(node.drop_high)[1] if node.drop_high else None
        drop_low = self.visit(node.drop_low)[1] if node.drop_low else None
        keep_high = self.visit(node.keep_high)[1] if node.keep_high else None
        keep_low = self.visit(node.keep_low)[1] if node.keep_low else None
        minimum = self.visit(node.minimum)[1] if node.minimum else None
        maximum = self.visit(node.maximum)[1] if node.maximum else None
        explode = self.visit(node.explode) if isinstance(node.explode, Predicate) else node.explode
        penetrate = self.visit(node.penetrate) if isinstance(node.penetrate, Predicate) else node.penetrate
        reroll = self.visit(node.reroll) if isinstance(node.reroll, Predicate) else node.reroll
        success = self.visit(node.success) if isinstance(node.success, Predicate) else None
        failure = self.visit(node.failure) if isinstance(node.failure, Predicate) else None
        ddice = DDice(
            self._int(count),
            self._int(sides),
            self._int(drop_high),
            self._int(drop_low),
            self._int(keep_high),
            self._int(keep_low),
            self._int(minimum),
            self._int(maximum),

            explode,
            penetrate,
            reroll,
            node.reroll_once,

            success,
            failure
        )
        roll_result = DiceRoller(ddice).roll()
        return repr(roll_result), roll_result.value

class Printer(IEvaluator):
    def visit_BinOp(self, node: BinOp) -> str:
        left = self.visit(node.left)
        right = self.visit(node.right)
        operator = node.operator
        op = ""
        if operator.tt == TT.PLUS:
            op = "+"
        elif operator.tt == TT.MINUS:
            op = "-"
        elif operator.tt == TT.STAR:
            op = "*"
        elif operator.tt == TT.DIV:
            op = "/"
        elif operator.tt == TT.CARET:
            op = "^"
        return f"{left} {op} {right}"

    def visit_Unary(self, node: Unary) -> str:
        val = self.visit(node.value)
        operator = node.operator
        op = ""
        if operator.tt == TT.PLUS:
            op = "+"
        elif operator.tt == TT.MINUS:
            op = "-"
        return f"{op}{val}"

    def visit_Number(self, node: Number) -> str:
        return f"{float(node.value.data):g}"

    def visit_Grouping(self, node: Grouping) -> str:
        rep = self.visit(node.value)
        return f"({rep})"

    def visit_Predicate(self, node: Predicate) -> str:
        return {
            TT.NEQ: "<>",
            TT.EQ: "=",
            TT.GT: ">",
            TT.LT: "<",
            TT.GE: ">=",
            TT.LE: "<="
        }[node.predicate.tt] + self.visit(node.comp)

    def visit_Function(self, node: Function) -> str:
        return f"{node.name.name.data}({', '.join(param.name.data for param in node.parameters)}) = {self.visit(node.body)}"

    def visit_Variable(self, node: Variable) -> str:
        return node.name.data

    def visit_FuncCall(self, node: FuncCall) -> str:
        rep = self.visit(node.function)
        if isinstance(node.function, Function):
            rep = f"({rep})"
        reps = [self.visit(arg) for arg in node.arguments]
        rep += "(" + ", ".join(reps) + ")"
        return rep


    def visit_Dice(self, node: Dice) -> str:
        count = self.visit(node.count) if node.count else ""
        sides = self.visit(node.side) if node.side != "%" else "%"
        drop_high = self.visit(node.drop_high) if node.drop_high else None
        drop_low = self.visit(node.drop_low) if node.drop_low else None
        keep_high = self.visit(node.keep_high) if node.keep_high else None
        keep_low = self.visit(node.keep_low) if node.keep_low else None
        minimum = self.visit(node.minimum) if node.minimum else None
        maximum = self.visit(node.maximum) if node.maximum else None
        explode = self.visit(node.explode) if isinstance(node.explode, Predicate) else node.explode
        penetrate = self.visit(node.penetrate) if isinstance(node.penetrate, Predicate) else node.penetrate
        reroll = self.visit(node.reroll) if isinstance(node.reroll, Predicate) else node.reroll
        success = self.visit(node.success) if isinstance(node.success, Predicate) else None
        failure = self.visit(node.failure) if isinstance(node.failure, Predicate) else None
        rep = f"{count}d{sides}"
        if success:
            rep += success
            if failure:
                rep += f"f{failure}"
        if minimum is not None:
            rep += f"min{minimum}"
        if maximum is not None:
            rep += f"max{maximum}"
        if explode is not None:
            rep += "!"
            if explode is not True:
                rep += explode
        if penetrate is not None:
            rep += "!p"
            if penetrate is not True:
                rep += penetrate
        if reroll is not None:
            rep += "r"
            if node.reroll_once:
                rep += "o"
            if reroll is not True:
                rep += reroll
        if keep_high:
            rep += f"kh{keep_high}"
        if keep_low:
            rep += f"kl{keep_low}"
        if drop_high:
            rep += f"dh{drop_high}"
        if drop_low:
            rep += f"dl{drop_low}"
        return rep
