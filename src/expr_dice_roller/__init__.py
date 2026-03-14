from .lexer import Lexer
from .parser import Parser
from .evaluator import Evaluator, Printer, Environment
from dataclasses import dataclass

__all__ = ["format_expression", "EvaluationResult", "evaluate", "Environment", "Evaluator"]

def format_expression(expression: str) -> str:
    t = Parser(Lexer(expression).lex()).expression()
    if t:
        return Printer().visit(t)
    return ""

@dataclass
class EvaluationResult:
    environment: Environment
    representation: str
    value: float | None

def evaluate(expression: str, environment: Environment | None = None, assign_last_eval: bool = False) -> EvaluationResult:
    t = Parser(Lexer(expression).lex()).expression()
    if t:
        expr_eval = Evaluator(environment)
        rep, val = expr_eval.visit(t)
        if assign_last_eval:
            expr_eval.environment.assign("_", val)
        if isinstance(val, (float, int)):
            val = int(val) if val.is_integer() else val
        else:
            val = None
        return EvaluationResult(expr_eval.environment, rep, val)
    return EvaluationResult(environment, "", None)
