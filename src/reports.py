import functools
import logging
from datetime import datetime
from typing import Callable, Optional

import pandas as pd

from src.utils import load_transactions_for_3_months

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
    filemode="a",
    encoding="utf-8",
)


def save_report(file_name: Optional[str] = None):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> pd.DataFrame:
            try:
                logging.info(f"Вызов функции {func.__name__} с параметрами: {args}, {kwargs}")
                result = func(*args, **kwargs)

                if not isinstance(result, pd.DataFrame):
                    logging.error("Результат не является DataFrame")
                    raise ValueError("Ожидался результат типа DataFrame для записи в файл.")

                final_file_name = file_name or f"{func.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

                result.to_json(final_file_name, orient="records", force_ascii=False, indent=2)
                logging.info(f"Результат сохранен в файл: {final_file_name}")
                return result
            except Exception as e:
                logging.exception(f"Ошибка в декораторе save_report: {e}")
                raise

        return wrapper

    return decorator


@save_report("my_report.json")
def spending_by_weekday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    logging.info("Начало выполнения функции spending_by_weekday")
    try:
        if date is None:
            date = datetime.today().strftime("%Y-%m-%d")
            logging.info(f"Дата не указана, используется текущая: {date}")

        transactions = load_transactions_for_3_months("./data/operations.xlsx", date)
        # df = pd.DataFrame(transactions)
        df = transactions if isinstance(transactions, pd.DataFrame) else pd.DataFrame(transactions)

        if df.empty:
            logging.warning("Данные транзакций пусты")
            return pd.DataFrame(columns=["День недели", "Средние траты"])

        df["Дата операции"] = pd.to_datetime(df["Дата операции"])
        df = df[df["Сумма операции"] < 0]

        df["День недели"] = df["Дата операции"].dt.dayofweek.map(
            {0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"}
        )

        grouped = df.groupby("День недели", as_index=False)["Сумма операции"].mean()
        grouped.rename(columns={"Сумма операции": "Средние траты"}, inplace=True)

        all_days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        result = pd.DataFrame({"День недели": all_days})
        result = result.merge(grouped, on="День недели", how="left")
        result["Средние траты"] = result["Средние траты"].fillna(0.0).round(2)

        logging.info("Формирование отчета завершено успешно")
        return result

    except Exception as e:
        logging.exception(f"Ошибка в spending_by_weekday: {e}")
        return pd.DataFrame(columns=["День недели", "Средние траты"])
