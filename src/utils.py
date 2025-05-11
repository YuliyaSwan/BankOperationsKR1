import json
import logging
import math
import os
from calendar import monthrange
from datetime import datetime, timedelta
from decimal import Decimal
from functools import wraps
from typing import Any, Dict, List, Optional, Callable

import pandas as pd
import requests
from dotenv import load_dotenv
from pandas import DataFrame

# from xml.etree import ElementTree as ET


                                        ############################
                                        # 1. Веб-страница. Главная #
                                        ############################

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
    filemode="a",
    encoding="utf-8",
)


def time_for_greeting():
    """Функция возвращает Доброе утро/Добрый день/Добрый вечер/Доброй ночи в зависимости от текущего времени"""

    current_time_hour = datetime.now().hour
    if current_time_hour < 6:
        return "Доброй ночи"
    elif current_time_hour < 12:
        return "Доброе утро"
    elif current_time_hour < 18:
        return "Добрый день"
    else:
        return "Добрый вечер"


def get_date_period(date_time: str, date_format: str = "%Y-%m-%d %H:%M:%S") -> list[str]:
    """Функция принимает дату от пользователя и возвращает отчетный период"""
    logging.info("Определение отчетного периода для даты %s", date_time)
    day_end = datetime.strptime(date_time, date_format)
    day_start = day_end.replace(day=1)

    # Добавим конец дня
    day_end = day_end.replace(hour=23, minute=59, second=59)

    return [day_start.strftime("%d.%m.%Y %H:%M:%S"), day_end.strftime("%d.%m.%Y %H:%M:%S")]


def get_path_and_period(path_to_file: str, date_period: list) -> DataFrame:
    """Функция принимает путь до файла и отчетный период и возвращает таблицу данных с заданным периодом"""
    logging.info("Загрузка и фильтрация данных из файла: %s", path_to_file)
    df = pd.read_excel(path_to_file, sheet_name="Отчет по операциям")

    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)

    start_day = datetime.strptime(date_period[0], "%d.%m.%Y %H:%M:%S")
    end_day = datetime.strptime(date_period[1], "%d.%m.%Y %H:%M:%S")

    filtered_df = df[(df["Дата операции"] >= start_day) & (df["Дата операции"] <= end_day)]

    sorted_df = filtered_df.sort_values(by="Дата операции", ascending=True)
    logging.info("Фильтрация завершена. Количество операций: %d", len(sorted_df))
    return sorted_df


def get_card_number(sorted_df: DataFrame) -> list[dict]:
    """Функция принимает DataFrame и возвращает список карт с расходами"""
    logging.info("Анализ транзакций по картам")
    card_transaction = []
    card_sorted = sorted_df[["Номер карты", "Сумма операции"]]
    for i, row in card_sorted.iterrows():
        # print(i, row)
        if row["Сумма операции"] < 0:
            last_digits = str(row["Номер карты"]).replace("*", "").strip()[-4:]
            spent = abs(float(row["Сумма операции"]))
            cashback = round(spent / 100, 2)

            card_transaction.append({"last_digits": last_digits, "total_spent": round(spent, 2), "cashback": cashback})

    # Агрегация по номеру карты
    from collections import defaultdict

    aggregated = defaultdict(lambda: {"total_spent": 0.0, "cashback": 0.0})

    for item in card_transaction:
        digits = item["last_digits"]
        aggregated[digits]["total_spent"] += item["total_spent"]
        aggregated[digits]["cashback"] += item["cashback"]

    # Преобразуем в отсортированный список
    result = []
    for digits in sorted(aggregated.keys()):
        result.append(
            {
                "last_digits": digits,
                "total_spent": round(aggregated[digits]["total_spent"], 2),
                "cashback": round(aggregated[digits]["cashback"], 2),
            }
        )

    logging.info("Обнаружено %d уникальных карт", len(result))
    return result


def get_top_transactions(sorted_df: DataFrame, top_n: int = 5) -> list[dict]:
    """Возвращает топ-5 транзакций по абсолютной сумме платежа"""
    logging.info("Получение топ-%d транзакций", top_n)
    top_df = sorted_df.copy()

    top_df["abs_amount"] = top_df["Сумма операции"].abs()
    top_df = top_df.sort_values(by="abs_amount", ascending=False).head(top_n)

    top_transactions = []
    for _, row in top_df.iterrows():
        top_transactions.append(
            {
                "date": row["Дата операции"].strftime("%d.%m.%Y"),
                "amount": round(row["Сумма операции"], 2),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )

    logging.info("Топ транзакции сформированы")
    return top_transactions


def get_currency_rates(json_path: str) -> list[dict]:
    """Получает курсы валют, указанных в JSON-файле, по отношению к RUB"""

    logging.info(f"Получение списка валют из {json_path}")
    # Загружаем переменные окружения из файла .env
    load_dotenv(".env")
    API_KEY = os.getenv("API_KEY_1")

    # Чтение валют из JSON
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            prefs = json.load(f)
            currencies = prefs.get("user_currencies", [])
        logging.info(f"Загружены валюты: {currencies}")
    except Exception as e:
        logging.error(f"Ошибка при чтении JSON: {e}", exc_info=True)
        return []  # Обработка ошибки, возвращаем пустой список

    if not currencies:
        logging.warning("Список валют пуст.")
        return []  # Если список пустой, возвращаем пустой список

    headers = {"apikey": API_KEY}
    result = []

    for code in currencies:
        try:
            url = f"https://api.apilayer.com/exchangerates_data/convert?to=RUB&from={code}&amount=1"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            rate = data.get("result")
            if rate:
                result.append({"currency": code, "rate": float(round(Decimal(str(rate)), 2))})
                logging.info(f"Получен курс для {code}: {rate}")
        except Exception as e:
            logging.error(f"Ошибка при получении курса для {code}: {e}", exc_info=True)
            continue

    return result

    # date_req = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
    # url = f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={date_req}"
    #
    # response = requests.get(url)
    # response.encoding = 'windows-1251'
    #
    # if not response.ok:
    #     raise ValueError("Ошибка при запросе к API ЦБ РФ")
    #
    # root = ET.fromstring(response.text)
    #
    # rates = []
    # for currency_code in ["USD", "EUR"]:
    #     valute = root.find(f"./Valute[CharCode='{currency_code}']")
    #     if valute is not None:
    #         rate = float(valute.find("Value").text.replace(",", "."))
    #         rates.append({
    #             "currency": currency_code,
    #             "rate": round(rate, 2)
    #         })
    #
    # return rates


def get_sp500_stock_prices(json_path: str) -> list[dict]:
    """Получает текущие цены акций, указанных в JSON-файле"""

    logging.info(f"Получение списка акций из {json_path}")
    # Загрузка API-ключа
    load_dotenv(".env")
    API_KEY = os.getenv("API_KEY_2")

    # Чтение тикеров акций из JSON
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            stocks = settings.get("user_stocks", [])
            logging.info(f"Загружены тикеры акций: {stocks}")
    except Exception as e:
        logging.error(f"Ошибка при чтении JSON-файла: {e}", exc_info=True)
        return []  # Обработка ошибки, возвращаем пустой список

    if not stocks:
        logging.warning("Список акций пуст.")
        return []  # Если список пустой, возвращаем пустой список

    symbols = ",".join(stocks)
    url = f"https://financialmodelingprep.com/api/v3/quote/{symbols}?apikey={API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        stock_prices = []
        for item in data:
            stock_prices.append({"stock": item["symbol"], "price": round(float(item["price"]), 2)})
        logging.info("Цены акций успешно получены")
        return stock_prices
    except Exception as e:
        logging.error("Ошибка при получении цен акций: %s", e, exc_info=True)
        return []

                                    ##############################
                                    # 2. Сервисы.  Инвесткопилка #
                                    ##############################


def get_month_period(month: str, date_format: str = "%Y-%m-%d %H:%M:%S") -> list[str]:
    """
    Принимает месяц в формате 'YYYY-MM' и возвращает отчетный период с 1-ого по последний день месяца.
    """
    logging.info(f"Получение периода для месяца: {month}")

    dt = datetime.strptime(month, "%Y-%m")
    start_date = dt.replace(day=1)
    last_day = monthrange(dt.year, dt.month)[1]
    end_date = dt.replace(day=last_day, hour=23, minute=59, second=59)
    period = [start_date.strftime(date_format), end_date.strftime(date_format)]

    logging.debug(f"Период: {period}")
    return period


def load_transactions_from_excel(path_to_file: str, month: str) -> List[Dict[str, Any]]:
    """
    Загружает данные из Excel-файла и возвращает транзакции за указанный месяц (формат 'YYYY-MM').
    Возвращает список словарей с ключами 'Дата операции' и 'Сумма операции'.
    """
    logging.info(f"Загрузка транзакций из файла: {path_to_file} за месяц: {month}")

    df = pd.read_excel(path_to_file, sheet_name="Отчет по операциям")
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)

    year, month_num = map(int, month.split("-"))
    start_date = datetime(year, month_num, 1)
    end_date = datetime(year, month_num, monthrange(year, month_num)[1])

    df_filtered = df[(df["Дата операции"] >= start_date) & (df["Дата операции"] <= end_date)]

    transactions = [
        {"Дата операции": row["Дата операции"].strftime("%Y-%m-%d"), "Сумма операции": float(row["Сумма операции"])}
        for _, row in df_filtered.iterrows()
        if not pd.isna(row["Сумма операции"])
    ]

    logging.info(f"Загружено {len(transactions)} транзакций")
    return transactions


def get_limit_transaction(limit: int, transactions: list[dict[str, float]]) -> float:
    """
    Принимает лимит округления и список операций за указанный месяц.
    Возвращает сумму, которую можно было бы отложить, округляя расходы вверх до ближайшего лимита.
    """
    savings = 0.0
    logging.info(f"Лимит округления: {limit} ₽")

    for transaction in transactions:
        amount = transaction.get("Сумма операции", 0)
        if amount < 0:
            abs_amount = abs(amount)
            rounded_up = math.ceil(abs_amount / limit) * limit
            saved = rounded_up - abs_amount
            savings += saved
            logging.debug(f"Операция: {abs_amount}, округлено до: {rounded_up}, накоплено: {saved}")
    total = round(savings, 2)
    logging.info(f"Общая сумма накоплений: {total}")
    return total


                                    ############################################
                                    # 3. Отчеты. Траты в рабочий/выходной день #
                                    ############################################


# def log_execution(func: Callable) -> Callable:
#     """
#     Декоратор логирования вызова функции.
#     """
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         logging.info(f"Вызов функции: {func.__name__}")
#         result = func(*args, **kwargs)
#         logging.info(f"Завершение функции: {func.__name__}")
#         return result
#     return wrapper

# def save_report(file_name: Optional[str] = None):
#     """
#     Декоратор для сохранения результата функции-отчета в JSON-файл.
#     """
#     def decorator(func: Callable):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             result = func(*args, **kwargs)
#             out_file = file_name or f"{func.__name__}_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
#             try:
#                 with open(out_file, "w", encoding="utf-8") as f:
#                     if isinstance(result, pd.DataFrame):
#                         result.to_json(f, orient='records', force_ascii=False, indent=4)
#                     else:
#                         json.dump(result, f, ensure_ascii=False, indent=4)
#                 logging.info(f"Отчет сохранен в файл: {out_file}")
#             except Exception as e:
#                 logging.error(f"Ошибка при сохранении отчета: {e}")
#             return result
#         return wrapper
#     return decorator if file_name is not None else decorator(None)


def load_transactions_for_3_months(path_to_file: str, date: str) -> List[Dict[str, Any]]:
    """
    Загружает данные из Excel-файла и возвращает транзакции за 3 месяца от указанной даты (формат 'YYYY-MM-DD').
    Возвращает список словарей с ключами 'Дата операции' и 'Сумма операции'.

    Принимает путь к Excel-файлу с транзакциями и дату в формате 'YYYY-MM-DD' для отсчета 3 месяцев.
    Возвращает список словарей с транзакциями за последние 3 месяца.
    """

    try:
        # Преобразуем строку с датой в объект datetime
        end_date = datetime.strptime(date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        start_date = end_date - timedelta(days=90)

        logging.info(
            f"Загрузка транзакций из файла: {path_to_file} за период с {start_date.date()} по {end_date.date()}")

        # Загрузка данных из Excel
        df = pd.read_excel(path_to_file)

        # Проверка на наличие нужных колонок
        if 'Дата операции' not in df.columns or 'Сумма операции' not in df.columns:
            raise ValueError("В файле отсутствуют необходимые колонки 'Дата операции' или 'Сумма операции'.")

        # Преобразование столбца с датами в тип datetime
        df['Дата операции'] = pd.to_datetime(df['Дата операции'], dayfirst=True)

        # Фильтрация по дате
        df_filtered = df[(df['Дата операции'] >= start_date) & (df['Дата операции'] <= end_date)]


        transactions = [
            {"Дата операции": row["Дата операции"].strftime("%Y-%m-%d"), "Сумма операции": float(row["Сумма операции"])}
            for _, row in df_filtered.iterrows()
            if not pd.isna(row["Сумма операции"])
        ]

        logging.info(f"Количество загруженных транзакций: {len(transactions)}")

        return transactions

    except Exception as e:
        logging.error(f"Ошибка при загрузке транзакций: {e}")
        return []
