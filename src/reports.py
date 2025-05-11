import json
from datetime import datetime, timedelta

import pandas as pd
from typing import Optional

from src.utils import load_transactions_for_3_months


def spending_by_weekday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """
    Возвращает средние траты по дням недели за последние 3 месяца от указанной даты (или текущей, если не указана).
    Учитываются только отрицательные суммы (траты).

    Принимает DataFrame с колонками 'Дата операции' и 'Сумма операции' и строку даты в формате 'YYYY-MM-DD' (опционально)
    Возвращает DataFrame со средними тратами по дням недели
    """

    if date is None:
        date = datetime.today().strftime('%Y-%m-%d')

    # Загружаем транзакции за 3 месяца
    transactions = load_transactions_for_3_months("./data/operations.xlsx", date)
    df = pd.DataFrame(transactions)

    if df.empty:
        return pd.DataFrame(columns=["День недели", "Средние траты"])

        # Преобразование даты
    df['Дата операции'] = pd.to_datetime(df['Дата операции'])

    # Оставляем только траты
    df = df[df['Сумма операции'] < 0]

    # Преобразуем номер дня недели в название
    df['День недели'] = df['Дата операции'].dt.dayofweek.map({
        0: 'Понедельник', 1: 'Вторник', 2: 'Среда',
        3: 'Четверг', 4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
    })

    # Группируем и считаем среднее
    grouped = df.groupby('День недели', as_index=False)['Сумма операции'].mean()
    grouped.rename(columns={'Сумма операции': 'Средние траты'}, inplace=True)

    # Создаем полную таблицу с нулями, если дней нет
    all_days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    result = pd.DataFrame({'День недели': all_days})
    result = result.merge(grouped, on='День недели', how='left')
    result['Средние траты'] = result['Средние траты'].fillna(0.0).round(2)

    # Добавляем один раз колонку с периодом
    # end_date = datetime.strptime(date, '%Y-%m-%d')
    # start_date = end_date - timedelta(days=90)
    # period_str = f"{start_date.date()} — {end_date.date()}"
    # result.insert(0, 'Период', None)
    # result.at[0, 'Период'] = period_str

    return result
