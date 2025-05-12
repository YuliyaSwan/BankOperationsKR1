import json
from unittest.mock import patch

import pytest

from src.services import investment_bank


@pytest.fixture
def example_transactions():
    return [
        {"Дата операции": "2024-04-01", "Сумма операции": -123.45},
        {"Дата операции": "2024-04-10", "Сумма операции": -50.10},
        {"Дата операции": "2024-04-15", "Сумма операции": 200.00},  # доход, не учитывается
    ]


@patch("src.services.load_transactions_from_excel")
def test_investment_bank_returns_correct_json(mock_load, example_transactions):
    # Подготовка
    mock_load.return_value = example_transactions
    test_month = "2024-04"
    test_limit = 50

    # Ожидаемый результат
    expected_savings = 76.45  # см. расчёты в get_limit_transaction
    expected_json = {"month": test_month, "limit": test_limit, "savings": expected_savings}

    # Вызов
    result_json_str = investment_bank(test_month, example_transactions, test_limit)

    # Проверка
    result = json.loads(result_json_str)
    assert result == expected_json
