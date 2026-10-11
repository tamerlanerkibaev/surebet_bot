# calculator.py
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


def calculate_surebet(
    k1: float,
    k2: float,
    bank: float,
    round_step: int = 1000,
    min_profit_percent: float = 1.0,
) -> SurebetResult:
    """Рассчитывает арбитражную ситуацию для двухисходного рынка.

    :param k1: Коэффициент наИсход 1
    :param k2: Коэффициент на Исход 2
    :param bank: Доступный банк для распределения
    :param round_step: Шаг округления ставок (например, 100, 500, 1000)
    :param min_profit_percent: Минимальный порог доходности (%)
    """
    if k1 <= 1.0 or k2 <= 1.0 or bank <= 0:
        return SurebetResult(
            has_surebet=False,
            k1=k1,
            k2=k2,
            s1=0,
            s2=0,
            total_spent=0,
            min_payout=0.0,
            profit=0.0,
            profit_percent=0.0,
            reason="Некорректные входные данные",
        )

    # 1. Проверка фундаментального условия вилки: 1/K1 + 1/K2 < 1
    inv_sum = (1.0 / k1) + (1.0 / k2)
    if inv_sum >= 1.0:
        return SurebetResult(
            has_surebet=False,
            k1=k1,
            k2=k2,
            s1=0,
            s2=0,
            total_spent=0,
            min_payout=0.0,
            profit=0.0,
            profit_percent=0.0,
            reason="Математический арбитраж отсутствует (маржа букмекера)",
        )

    # 2. Идеальное расчётно-оптимальное распределение
    s1_ideal = bank * (1.0 / k1) / inv_sum
    s2_ideal = bank * (1.0 / k2) / inv_sum

    # 3. Округление ставок до заданного шага (100 / 500 / 1000 ₸)
    s1 = int(round(s1_ideal / round_step) * round_step)
    s2 = int(round(s2_ideal / round_step) * round_step)

    if s1 <= 0 or s2 <= 0:
        return SurebetResult(
            has_surebet=False,
            k1=k1,
            k2=k2,
            s1=s1,
            s2=s2,
            total_spent=s1 + s2,
            min_payout=0.0,
            profit=0.0,
            profit_percent=0.0,
            reason="Шаг округления слишком велик для указанного банка",
        )

    total_spent = s1 + s2

    # 4. Выплаты при каждом исходе и проверка после округления
    payout_1 = s1 * k1
    payout_2 = s2 * k2
    min_payout = min(payout_1, payout_2)

    profit = min_payout - total_spent
    profit_percent = (profit / total_spent) * 100.0 if total_spent > 0 else 0.0

    # 5. Фильтрация: проверяем, остался ли профит положительным и выше ли он порога
    if profit <= 0:
        return SurebetResult(
            has_surebet=False,
            k1=k1,
            k2=k2,
            s1=s1,
            s2=s2,
            total_spent=total_spent,
            min_payout=round(min_payout, 2),
            profit=round(profit, 2),
            profit_percent=round(profit_percent, 2),
            reason="Вилка исчезла или ушла в убыток после округления ставок",
        )

    if profit_percent < min_profit_percent:
        return SurebetResult(
            has_surebet=False,
            k1=k1,
            k2=k2,
            s1=s1,
            s2=s2,
            total_spent=total_spent,
            min_payout=round(min_payout, 2),
            profit=round(profit, 2),
            profit_percent=round(profit_percent, 2),
            reason=f"Доходность ({profit_percent:.2f}%) ниже заданного порога ({min_profit_percent}%)",
        )

    return SurebetResult(
        has_surebet=True,
        k1=k1,
        k2=k2,
        s1=s1,
        s2=s2,
        total_spent=total_spent,
        min_payout=round(min_payout, 2),
        profit=round(profit, 2),
        profit_percent=round(profit_percent, 2),
    )


# --- Модульные тесты/проверка калькулятора ---
if __name__ == "__main__":
    test_k1, test_k2 = 2.10, 2.05
    test_bank = 1_000_000

    print("=== ТЕСТ КАЛЬКУЛЯТОРА (Шаг 1000 ₸) ===")
    res = calculate_surebet(
        test_k1, test_k2, test_bank, round_step=1000, min_profit_percent=1.0
    )

    if res.has_surebet:
        print(f"✅ ВИЛКА НАЙДЕНА: {res.profit_percent}%")
        print(f"Ставка 1 (K={res.k1}): {res.s1:,} ₸")
        print(f"Ставка 2 (K={res.k2}): {res.s2:,} ₸")
        print(f"Всего затрат: {res.total_spent:,} ₸")
        print(f"Мин. выплата: {res.min_payout:,} ₸")
        print(f"Чистая прибыль: {res.profit:,} ₸")
    else:
        print(f"❌ ОТКЛОНЕНО: {res.reason}")
