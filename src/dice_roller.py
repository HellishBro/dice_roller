from dataclasses import dataclass
from random import randint
import modifiers as mods
from modifiers import MAX_ITERATIONS


@dataclass
class Predicate:
    predicate: str
    comp: float

    def meet(self, value: int) -> bool:
        if self.predicate == "<>":
            return value != self.comp
        elif self.predicate == "=":
            return value == self.comp
        elif self.predicate == ">":
            return value > self.comp
        elif self.predicate == ">=":
            return value >= self.comp
        elif self.predicate == "<":
            return value < self.comp
        elif self.predicate == "<=":
            return value <= self.comp
        return False


class Roll:
    def __init__(self, value: int):
        self.value = value
        self.rep = "{}"
        self.value_override = None

    def __repr__(self) -> str:
        return self.rep.replace("{}", str(self.value))

    def reroll(self, new_roll):
        self.value = new_roll.value


@dataclass
class Dice:
    count: int | None
    side: int
    drop_high: int | None = None
    drop_low: int | None = None
    keep_high: int | None = None
    keep_low: int | None = None
    minimum: int | None = None
    maximum: int | None = None
    explode: Predicate | bool | None = None
    penetrate: Predicate | bool | None = None
    reroll: Predicate | bool | None = None
    reroll_once: bool = False
    success: Predicate | None = None
    failure: Predicate | None = None

    def roll_once(self) -> Roll:
        if self.side == 0: return Roll(0)
        if self.side >= 1: return Roll(randint(1, self.side))
        return Roll(randint(self.side, -1))

class RollResult:
    def __init__(self, rolls: list[Roll]):
        self.rolls = rolls

    @property
    def value(self) -> int:
        return sum(roll.value_override if roll.value_override is not None else roll.value for roll in self.rolls)

    def __repr__(self) -> str:
        return "[" + ", ".join(repr(roll) for roll in self.rolls) + "]"


class DiceRoller:
    def __init__(self, dice: Dice):
        self.dice = dice

    def roll(self) -> RollResult:
        res = RollResult([])
        count = self.dice.count if self.dice.count is not None else 1
        if count > 127:
            raise ValueError(f"{count} exceeds the dice limit.")

        for _ in range(count):
            res.rolls.append(self.dice.roll_once())

        modifiers: list[type[mods.Mod]] = []
        if self.dice.minimum: modifiers.append(mods.Min)
        if self.dice.maximum: modifiers.append(mods.Max)
        if self.dice.explode: modifiers.append(mods.Explode)
        if self.dice.penetrate: modifiers.append(mods.Penetrate)
        if self.dice.reroll: modifiers.append(mods.ReRoll)
        if self.dice.keep_high or self.dice.keep_low: modifiers.append(mods.Keep)
        if self.dice.drop_high or self.dice.drop_low: modifiers.append(mods.Drop)
        if self.dice.success or self.dice.failure: modifiers.append(mods.Success)
        for modifier in modifiers:
            modifier(self.dice).run(res)

        return res
