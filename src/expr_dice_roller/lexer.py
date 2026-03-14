from typing import Any
from enum import Enum, auto

class TT(Enum):
    NUMBER = auto() # int or float
    NAME = auto() # any string of characters not recognized by the lexer

    D = auto() # literal d (dice or drop)
    DL = auto() # literal dl (drop low)
    DH = auto() # literal dh (drop high)
    K = auto() # literal k (keep)
    KL = auto() # literal kl (keep low)
    KH = auto() # literal kh (keep high)
    MIN = auto() # literal min (min)
    MAX = auto() # literal max (max)
    R = auto() # literal r (reroll)
    RO = auto() # literal ro (reroll once)
    F = auto() # literal f (failure)

    PLUS = auto() # +
    MINUS = auto() # -
    STAR = auto() # *
    DIV = auto() # /
    CARET = auto() # ^

    PERCENT = auto() # %

    COMMA = auto() # ,

    BANG = auto() # literal ! (explode)
    BANG_P = auto() # literal !p (penetrate)
    GT = auto() # >
    GE = auto() # >=
    LT = auto() # <
    LE = auto() # <=
    EQ = auto() # =
    NEQ = auto() # <> or !=

    LPAREN = auto() # (
    RPAREN = auto() # )

    ERROR = auto()

token_names = {
    TT.NUMBER: "number",
    TT.NAME: "name",
    TT.D: "d",
    TT.DL: "dl",
    TT.DH: "dh",
    TT.K: "k",
    TT.KL: "kl",
    TT.KH: "kh",
    TT.MIN: "min",
    TT.MAX: "max",
    TT.R: "r",
    TT.RO: "ro",
    TT.F: "f",
    TT.PLUS: "+",
    TT.MINUS: "-",
    TT.STAR: "*",
    TT.DIV: "/",
    TT.PERCENT: "%",
    TT.COMMA: ",",
    TT.BANG: "!",
    TT.BANG_P: "!p",
    TT.GT: ">",
    TT.GE: ">=",
    TT.LT: "<",
    TT.LE: "<=",
    TT.EQ: "=",
    TT.NEQ: "<> or !=",
    TT.LPAREN: "(",
    TT.RPAREN: ")"
}

class Token:
    def __init__(self, tt: TT, pos: int, data: Any):
        self.tt = tt
        self.pos = pos
        self.data = data

    def __repr__(self) -> str:
        return f"Token({self.tt!r}, {self.pos!r}, {self.data!r})"


NAME_TTs = TT.NAME, TT.DL, TT.DH, TT.K, TT.KL, TT.KH, TT.MIN, TT.MAX, TT.R, TT.RO, TT.F

class Lexer:
    def __init__(self, sequence: str):
        self.sequence = sequence
        self.pos = 0
        self.start_pos = 0
        self.tokens = []

    def add_token(self, tt: TT, data: Any | None = None):
        self.tokens.append(Token(tt, self.start_pos, data or self.sequence[self.start_pos:self.pos]))

    def at_end(self) -> bool:
        return self.pos >= len(self.sequence)

    def peek(self) -> str: return self.sequence[self.pos] if not self.at_end() else "\0"

    def advance(self) -> str:
        char = self.peek()
        self.pos += 1
        return char

    def number(self, start: str):
        decimal = start == "."
        tt = TT.NUMBER
        dat = None
        while self.peek() in "1234567890.":
            if decimal and self.peek() == ".":
                tt = TT.ERROR
                dat = "Invalid number literal."
            elif self.peek() == "." and not decimal:
                decimal = True
            self.advance()
        self.add_token(tt, dat)

    def name(self):
        stop_characters = " \n\t\0()+-*/=,<>^!1234567890.%"
        while self.peek() not in stop_characters:
            self.advance()
        n = self.sequence[self.start_pos:self.pos]
        self.add_token({
            "d": TT.D,
            "dl": TT.DL,
            "dh": TT.DH,
            "k": TT.K,
            "kl": TT.KL,
            "kh": TT.KH,
            "min": TT.MIN,
            "max": TT.MAX,
            "r": TT.R,
            "ro": TT.RO,
            "f": TT.F
        }.get(n, TT.NAME))


    def token(self):
        char = self.advance()
        if char == "#":
            while self.advance() not in "\n\0":
                pass
            return

        if char in " \n\t": return
        if char in "1234567890.":
            self.number(char)
        elif char in "+-*/()=,^%":
            mapping  = {"+": TT.PLUS, "-": TT.MINUS, "*": TT.STAR, "/": TT.DIV, "(": TT.LPAREN, ")": TT.RPAREN, "=": TT.EQ, ",": TT.COMMA, "^": TT.CARET, "%": TT.PERCENT}
            self.add_token(mapping[char])
        elif char == ">":
            if self.peek() == "=":
                self.advance()
                self.add_token(TT.GE)
            else:
                self.add_token(TT.GT)
        elif char == "<":
            if self.peek() == "=":
                self.advance()
                self.add_token(TT.LE)
            elif self.peek() == ">":
                self.advance()
                self.add_token(TT.NEQ)
            else:
                self.add_token(TT.LT)
        elif char == "!":
            if self.peek() == "=":
                self.advance()
                self.add_token(TT.NEQ)
            elif self.peek() == "p":
                self.advance()
                self.add_token(TT.BANG_P)
            else:
                self.add_token(TT.BANG)
        else:
            self.name()

    def lex(self) -> list[Token]:
        while not self.at_end():
            self.start_pos = self.pos
            self.token()
        return self.tokens
