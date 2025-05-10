from src.views import main_info
import pandas as pd
import json
from unittest.mock import patch


@patch("src.views.get_currency_rates")
@patch("src.views.get_sp500_stock_prices")
@patch("src.views.get_top_transactions")
@patch("src.views.get_card_number")
@patch("src.views.get_path_and_period")
@patch("src.views.get_date_period")
@patch("src.views.time_for_greeting")
def test_main_info(mock_greet, mock_period, mock_path, mock_card, mock_top, mock_rates, mock_stocks):
    mock_greet.return_value = "Доброе утро"
    mock_period.return_value = ["01.05.2024 00:00:00", "31.05.2024 23:59:59"]
    mock_path.return_value = pd.DataFrame()
    mock_card.return_value = [{"last_digits": "1234", "total_spent": 100.0, "cashback": 1.0}]
    mock_top.return_value = [{"date": "01.05.2024", "amount": -100.0, "category": "Еда", "description": "Ресторан"}]
    mock_rates.return_value = [{"currency": "USD", "rate": 82.45}]
    mock_stocks.return_value = [{"stock": "AAPL", "price": 180.01}]

    result = main_info("2024-05-15 12:00:00")
    result_dict = json.loads(result)
    assert result_dict["greeting"] == "Доброе утро"
    assert result_dict["cards"]
    assert result_dict["top_transactions"]
    assert result_dict["currency_rates"]
    assert result_dict["stock_prices"]