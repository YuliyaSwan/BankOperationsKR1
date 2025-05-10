import os
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytest

from src.utils import (get_card_number, get_currency_rates, get_date_period, get_limit_transaction, get_month_period,
                       get_path_and_period, get_sp500_stock_prices, get_top_transactions, load_transactions_from_excel,
                       time_for_greeting)

# -------- FIXTURES --------


@pytest.fixture
def sample_dataframe():
    data = {
        "Дата операции": pd.to_datetime(["2024-05-01", "2024-05-03", "2024-05-05"]),
        "Номер карты": ["****1234", "****1234", "****5678"],
        "Сумма операции": [-100.0, -200.0, -300.0],
        "Категория": ["Еда", "Транспорт", "Развлечения"],
        "Описание": ["Ресторан", "Метро", "Кино"],
    }
    return pd.DataFrame(data)


# @pytest.fixture
# def sample_json(tmp_path):
#     path = tmp_path / "settings.json"
#     content = {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "GOOG"]}
#     path.write_text(json.dumps(content), encoding="utf-8")
#     return str(path)


# -------- TESTS --------


def test_time_for_greeting():
    with patch("src.utils.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1, 9)
        assert time_for_greeting() == "Доброе утро"

        mock_datetime.now.return_value = datetime(2024, 1, 1, 14)
        assert time_for_greeting() == "Добрый день"

        mock_datetime.now.return_value = datetime(2024, 1, 1, 20)
        assert time_for_greeting() == "Добрый вечер"

        mock_datetime.now.return_value = datetime(2024, 1, 1, 3)
        assert time_for_greeting() == "Доброй ночи"


def test_get_date_period():
    date = "2024-05-10 15:30:00"
    result = get_date_period(date)
    assert result[0].startswith("01.05.2024")
    assert result[1].startswith("10.05.2024")


@patch("pandas.read_excel")
def test_get_path_and_period(mock_read_excel, sample_dataframe):
    mock_read_excel.return_value = sample_dataframe
    date_period = ["01.05.2024 00:00:00", "31.05.2024 23:59:59"]
    result = get_path_and_period("fake.xlsx", date_period)
    assert len(result) == 3


def test_get_card_number(sample_dataframe):
    result = get_card_number(sample_dataframe)
    assert isinstance(result, list)
    assert result[0]["last_digits"] == "1234"
    assert result[0]["total_spent"] == 300.0
    assert result[0]["cashback"] == 3.0


def test_get_top_transactions(sample_dataframe):
    result = get_top_transactions(sample_dataframe, top_n=2)
    assert len(result) == 2
    assert result[0]["category"] in ["Развлечения", "Транспорт"]


@patch("builtins.open", new_callable=mock_open, read_data='{"user_currencies": ["USD", "EUR"]}')
@patch("requests.get")
@patch.dict(os.environ, {"API_KEY_1": "testkey"})
def test_get_currency_rates(mock_get, mock_file):
    mock_response = MagicMock()
    mock_response.json.side_effect = [
        {"result": 82.4552},
        {"result": 92.7919},
    ]
    mock_response.raise_for_status = lambda: None
    mock_get.return_value = mock_response

    result = get_currency_rates("settings.json")
    assert result == [{"currency": "USD", "rate": 82.46}, {"currency": "EUR", "rate": 92.79}]


@patch("builtins.open", new_callable=mock_open, read_data='{"user_currencies": ["USD", "BAD"]}')
@patch("requests.get")
@patch.dict(os.environ, {"API_KEY_1": "testkey"})
def test_get_currency_rates_with_api_error(mock_get, mock_file):
    # Мокируем успешный ответ для USD
    def side_effect(url, headers):
        if "USD" in url:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"result": 82.45}
            mock_resp.raise_for_status = lambda: None
            return mock_resp
        else:
            raise Exception("API Error for BAD")

    mock_get.side_effect = side_effect

    result = get_currency_rates("settings.json")
    assert result == [{"currency": "USD", "rate": 82.45}]


@patch("builtins.open", new_callable=mock_open, read_data='{"user_stocks": ["AAPL", "GOOG"]}')
@patch("requests.get")
@patch.dict(os.environ, {"API_KEY_2": "testkey"})
def test_get_sp500_stock_prices(mock_get, mock_file):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"symbol": "AAPL", "price": 180.01},
        {"symbol": "GOOG", "price": 2550.55},
    ]
    mock_response.raise_for_status = lambda: None
    mock_get.return_value = mock_response

    result = get_sp500_stock_prices("settings.json")
    assert result == [
        {"stock": "AAPL", "price": 180.01},
        {"stock": "GOOG", "price": 2550.55},
    ]


@patch("builtins.open", new_callable=mock_open, read_data='{"user_stocks": ["AAPL", "BAD"]}')
@patch("requests.get")
@patch.dict(os.environ, {"API_KEY_2": "testkey"})
def test_get_sp500_stock_prices_with_api_error(mock_get, mock_file):
    # Мокируем успешный ответ для AAPL и ошибку для BAD
    def side_effect(url):
        if "AAPL" in url:
            mock_resp = MagicMock()
            mock_resp.json.return_value = [{"symbol": "AAPL", "price": 180.01}]
            mock_resp.raise_for_status = lambda: None
            return mock_resp

    mock_get.side_effect = side_effect

    result = get_sp500_stock_prices("settings.json")
    assert result == [{"stock": "AAPL", "price": 180.01}]


@patch("builtins.open", new_callable=mock_open, read_data='{"user_stocks": ["AAPL", "GOOG"]}')
@patch("requests.get", side_effect=Exception("Request failed"))
@patch.dict(os.environ, {"API_KEY_2": "testkey"})
def test_get_sp500_stock_prices_request_error(mock_get, mock_file):
    result = get_sp500_stock_prices("settings.json")
    assert result == []


@patch("builtins.open", new_callable=mock_open, read_data='{"user_currencies": []}')
@patch.dict(os.environ, {"API_KEY_1": "testkey"})
def test_get_currency_rates_empty_list(mock_file):
    result = get_currency_rates("settings.json")
    assert result == []


@patch("builtins.open", new_callable=mock_open, read_data='{"user_stocks": []}')
def test_get_sp500_stock_prices_empty_list(mock_file):
    result = get_sp500_stock_prices("settings.json")
    assert result == []

    ##############################
    # 2. Сервисы.  Инвесткопилка #
    ##############################


@pytest.fixture
def example_transactions():
    return [
        {"Сумма операции": -123.45},
        {"Сумма операции": -50.10},
        {"Сумма операции": 300.00},  # доход, не участвует
    ]


def test_get_month_period():
    period = get_month_period("2024-04")
    assert period == ["2024-04-01 00:00:00", "2024-04-30 23:59:59"]


def test_get_limit_transaction(example_transactions):
    result = get_limit_transaction(50, example_transactions)
    # Расчёт:
    # -123.45 → округляется до 150 → накоплено 26.55
    # -50.10 → округляется до 100 → накоплено 49.90
    # итого = 76.45
    assert result == pytest.approx(76.45, 0.01)


@patch("pandas.read_excel")
def test_load_transactions_from_excel(mock_read_excel, tmp_path):
    test_file = tmp_path / "test.xlsx"
    test_month = "2024-04"

    # Подготовим тестовый DataFrame
    data = {"Дата операции": ["01.04.2024", "15.04.2024"], "Сумма операции": [-100.0, -200.0]}
    df_mock = pd.DataFrame(data)
    df_mock["Дата операции"] = pd.to_datetime(df_mock["Дата операции"], dayfirst=True)
    mock_read_excel.return_value = df_mock

    # Выполнение
    result = load_transactions_from_excel(str(test_file), test_month)

    # Проверка
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == {"Дата операции": "2024-04-01", "Сумма операции": -100.0}
    assert result[1] == {"Дата операции": "2024-04-15", "Сумма операции": -200.0}
