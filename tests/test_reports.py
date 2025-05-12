from unittest import mock
from unittest.mock import patch

import pandas as pd
import pytest

from src.reports import save_report, spending_by_weekday


@pytest.fixture
def empty_transactions():
    return []


@patch("src.utils.load_transactions_for_3_months")
def test_spending_by_weekday_empty(mock_load, empty_transactions):
    mock_load.return_value = empty_transactions
    date = "2024-12-10"
    result = spending_by_weekday(pd.DataFrame(), date)
    assert result.empty or result["Средние траты"].sum() == 0


@patch("src.utils.load_transactions_for_3_months", side_effect=Exception("Ошибка загрузки"))
def test_spending_by_weekday_exception(mock_load):
    date = "2024-12-10"
    result = spending_by_weekday(pd.DataFrame(), date)
    assert result.empty


def test_spending_by_weekday_with_invalid_date_format():
    df = pd.DataFrame([{"Дата операции": "не-дата", "Сумма операции": -1000}])
    result = spending_by_weekday(df)
    assert result.empty or result["Средние траты"].sum() == 0.0


@pytest.mark.parametrize(
    "return_value, expected_error_message",
    [
        (
            "string_instead_of_dataframe",
            "Ошибка в декораторе save_report: Ожидался результат типа DataFrame для записи в файл.",
        ),
        (12345, "Ошибка в декораторе save_report: Ожидался результат типа DataFrame для записи в файл."),
    ],
)
def test_save_report_invalid_return_value(return_value, expected_error_message):
    # Мокаем функцию, чтобы она возвращала неверный тип данных
    @save_report()
    def mock_function():
        return return_value  # Возвращаем неправильный тип данных

    with (
        mock.patch("logging.error") as mock_error,
        pytest.raises(ValueError, match="Ожидался результат типа DataFrame"),
    ):
        mock_function()

    # Проверяем, что логирование вызвано с правильным сообщением
    mock_error.assert_called_with(expected_error_message, exc_info=True)


def test_spending_by_weekday_exception_handling():
    # Мокаем load_transactions_for_3_months, чтобы он выбросил исключение
    with (
        mock.patch("src.reports.load_transactions_for_3_months", side_effect=RuntimeError("Ошибка загрузки")),
        mock.patch("logging.exception") as mock_log_exception,
    ):

        # Вызываем функцию
        result = spending_by_weekday(pd.DataFrame(), "2024-12-01")

        # Проверка: вернулся пустой DataFrame с нужными колонками
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["День недели", "Средние траты"]
        assert result.empty

        # Проверка: logging.exception вызвался с нужным сообщением
        mock_log_exception.assert_called()
        assert "Ошибка в spending_by_weekday" in mock_log_exception.call_args[0][0]


def test_spending_by_weekday_includes_all_days():
    # Данные только для понедельника и среды
    mock_data = pd.DataFrame(
        {
            "Дата операции": pd.to_datetime(["2024-12-02", "2024-12-04"]),  # Пн и Ср
            "Сумма операции": [-120.5, -300.75],
        }
    )

    with mock.patch("src.reports.load_transactions_for_3_months", return_value=mock_data):
        result = spending_by_weekday(mock_data, "2024-12-10")

        expected_days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

        # Проверка всех 7 дней
        assert list(result["День недели"]) == expected_days

        # Проверка округления и заполнения пропусков
        assert result[result["День недели"] == "Понедельник"]["Средние траты"].iloc[0] == -120.5
        assert result[result["День недели"] == "Среда"]["Средние траты"].iloc[0] == -300.75
        assert result[result["День недели"] == "Пятница"]["Средние траты"].iloc[0] == 0.0
