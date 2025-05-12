import json
import logging
# from datetime import datetime
from typing import Any, Dict, List

from src.utils import get_limit_transaction, load_transactions_from_excel

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
    filemode="a",
    encoding="utf-8",
)


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Сервис «Инвесткопилка»: принимает месяц 'YYYY-MM' для расчета, транзакции в формате списка словарей
    и лимит округления. Возвращает сумму возможных накоплений.
    """
    logging.info(f"Запуск инвестиционного сервиса за {month} с лимитом {limit}")

    # month_period = get_month_period(month)
    # start_dt = datetime.strptime(month_period[0], "%Y-%m-%d %H:%M:%S")
    # end_dt = datetime.strptime(month_period[1], "%Y-%m-%d %H:%M:%S")
    transactions = load_transactions_from_excel("./data/operations.xlsx", month)

    result = get_limit_transaction(limit, transactions)
    logging.info(f"Сумма накоплений за {month}: {result}")

    response = {"month": month, "limit": limit, "savings": result}

    response_json = json.dumps(response, ensure_ascii=False, indent=4)

    return response_json
