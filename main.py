# from src.reports import spending_by_weekday
import pandas as pd

from src.reports import spending_by_weekday
from src.services import investment_bank
from src.utils import load_transactions_from_excel, load_transactions_for_3_months
from src.views import main_info

if __name__ == "__main__":
    # print(main_info("2018-05-20 00:00:00"))

    # transactions = load_transactions_from_excel("./data/operations.xlsx", "2018-05")
    # print(investment_bank("2018-05", transactions, 50))

    transactions = load_transactions_for_3_months("./data/operations.xlsx", "2018-05-20")
    df = pd.DataFrame(transactions)
    # print(transactions)
    print(spending_by_weekday(df, "2018-05-20"))
