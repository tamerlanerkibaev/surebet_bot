from dataclasses import dataclass
from typing import Optional

@dataclass
class SurebetResult:
    has_surebet: bool
    k1: float
    k2: float
    s1: int
    s2: int
    total_spent: int
    min_payout: float
    profit: float
    profit_percent: float
    reason: Optional[str] = None

def calculate_surebet(k1: float, k2: float, bank: float, round_step: int = 1000, min_profit_percent: float = 1.0):
    if k1 <= 1.0 or k2 <= 1.0 or bank <= 0:
        return SurebetResult(False, k1, k2, 0, 0, 0, 0.0, 0.0, 0.0, "Некорректные входные данные")

    inv_sum = (1.0 / k1) + (1.0 / k2)
    if inv_sum >= 1.0:
        return SurebetResult(False, k1, k2, 0, 0, 0, 0.0, 0.0, 0.0, "Арбитраж отсутствует (маржа букмекера)")

    s1_ideal = bank * (1.0 / k1) / inv_sum
    s2_ideal = bank * (1.0 / k2) / inv_sum

    s1 = int(round(s1_ideal / round_step) * round_step)
    s2 = int(round(s2_ideal / round_step) * round_step)

    if s1 <= 0 or s2 <= 0:
        return SurebetResult(False, k1, k2, s1, s2, s1 + s2, 0.0, 0.0, 0.0, "Шаг округления слишком велик для банка")

    total_spent = s1 + s2
    payout_1 = s1 * k1
    payout_2 = s2 * k2
    min_payout = min(payout_1, payout_2)

    profit = min_payout - total_spent
    profit_percent = (profit / total_spent) * 100.0 if total_spent > 0 else 0.0

    if profit <= 0:
        return SurebetResult(False, k1, k2, s1, s2, total_spent, round(min_payout, 2), round(profit, 2), round(profit_percent, 2), "Вилка исчезла после округления")

    if profit_percent < min_profit_percent:
        return SurebetResult(False, k1, k2, s1, s2, total_spent, round(min_payout, 2), round(profit, 2), round(profit_percent, 2), f"Доходность ({profit_percent:.2f}%) ниже порога")

    return SurebetResult(True, k1, k2, s1, s2, total_spent, round(min_payout, 2), round(profit, 2), round(profit_percent, 2))