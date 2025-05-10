import json
import logging
import os
from datetime import datetime
from decimal import Decimal

import pandas as pd
import requests
from dotenv import load_dotenv
from pandas import DataFrame

# from xml.etree import ElementTree as ET


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
    filemode="a",
    encoding="utf-8"
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
