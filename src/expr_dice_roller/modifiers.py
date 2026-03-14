from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dice_roller import RollResult, Dice

MAX_ITERATIONS = 100

class Mod:
    def __init__(self, dice: Dice):
        self.dice = dice

    def run(self, res: RollResult): pass

class Min(Mod):
    def run(self, res: RollResult):
        for roll in res.rolls:
            if roll.value < self.dice.minimum:
                roll.value = self.dice.minimum
                roll.rep += "^"

class Max(Mod):
    def run(self, res: RollResult):
        for roll in res.rolls:
            if roll.value > self.dice.maximum:
                roll.value = self.dice.maximum
                roll.rep += "v"

class Explode(Mod):
    def run(self, res: RollResult):
        new_rolls = []
        pred = self.dice.explode
        for roll in res.rolls:
            subrolls = [roll]
            for i in range(MAX_ITERATIONS):
                if (pred is True and subrolls[i].value == self.dice.side) or (pred is not True and pred.meet(subrolls[i].value)):
                    subrolls[i].rep += "!"
                    subrolls.append(self.dice.roll_once())
                else:
                    break
            new_rolls.extend(subrolls)
        res.rolls = new_rolls

class Penetrate(Mod):
    def run(self, res: RollResult):
        new_rolls = []
        for roll in res.rolls:
            subrolls = [roll]
            pred = self.dice.penetrate
            for i in range(MAX_ITERATIONS):
                if (pred is True and subrolls[i].value == self.dice.side) or (pred is not True and pred.meet(subrolls[i].value)):
                    subrolls[i].rep += "!p"
                    new_roll = self.dice.roll_once()
                    new_roll.value -= 1
                    subrolls.append(new_roll)
                else:
                    break
            new_rolls.extend(subrolls)
        res.rolls = new_rolls

class ReRoll(Mod):
    def run(self, res: RollResult):
        pred = self.dice.reroll
        for roll in res.rolls:
            for i in range(MAX_ITERATIONS):
                if (pred is True and roll.value == 1) or pred.meet(roll.value):
                    roll.reroll(self.dice.roll_once())
                    if i == 1:
                        roll.rep += "r"
                        if self.dice.reroll_once:
                            roll.rep += "o"
                            break

class Keep(Mod):
    def run(self, res: RollResult):
        sorted_values = sorted(res.rolls, key=lambda r: r.value)
        invalidate_indices = [*range(len(res.rolls))]
        if self.dice.keep_high:
            del invalidate_indices[max(len(res.rolls) - self.dice.keep_high, 0):]
        if self.dice.keep_low:
            del invalidate_indices[:max(self.dice.keep_low, 0)]

        for index in set(invalidate_indices):
            dice = sorted_values[index]
            dice.value_override = 0
            dice.rep += "d"

class Drop(Mod):
    def run(self, res: RollResult):
        sorted_values = sorted(res.rolls, key=lambda r: r.value)
        invalidate_indices = []
        if self.dice.drop_low:
            invalidate_indices = [*range(self.dice.drop_low)]
        if self.dice.drop_high:
            invalidate_indices = [*range(max(len(res.rolls) - self.dice.drop_high, 0), len(res.rolls))]
        if len(invalidate_indices) > len(sorted_values):
            invalidate_indices = [*range(len(sorted_values))]

        for index in set(invalidate_indices):
            dice = sorted_values[index]
            if dice.value_override != 0:
                dice.value_override = 0
                dice.rep += "d"

class Success(Mod):
    def run(self, res: RollResult):
        for roll in res.rolls:
            if self.dice.success.meet(roll.value):
                roll.value_override = 1
                roll.rep += "*"
            elif self.dice.failure and self.dice.failure.meet(roll.value):
                roll.value_override = -1
                roll.rep += "_"
            else:
                roll.value_override = 0
