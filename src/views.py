import json
from typing import Any, Dict

from src.utils import (get_card_number, get_currency_rates, get_date_period, get_path_and_period,
                       get_sp500_stock_prices, get_top_transactions, time_for_greeting)


def main_info(date_time: str) -> Dict[str, Any]:
    """
    Функция, принимающая на вход строку с датой и временем в формате YYYY-MM-DD HH:MM:SS и возвращающую JSON-ответ
    2018-05-20 00:00:00
    """

    greeting = time_for_greeting()
    date_period = get_date_period(date_time)
    sorted_df = get_path_and_period("./data/operations.xlsx", date_period)

    cards = get_card_number(sorted_df)
    top_transactions = get_top_transactions(sorted_df)
    currency_rates = get_currency_rates(json_path="./data/user_settings.json")
    stock_prices = get_sp500_stock_prices(json_path="./data/user_settings.json")

    # print(date_period)

    data = {
        "greeting": greeting,
        "cards": cards,
        "top_transactions": top_transactions,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }

    json_data = json.dumps(data, ensure_ascii=False, indent=4)

    return json_data
