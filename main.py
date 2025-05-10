from src.services import investment_bank
from src.utils import load_transactions_from_excel
from src.views import main_info

if __name__ == "__main__":
    print(main_info("2018-05-20 00:00:00"))

    transactions = load_transactions_from_excel("./data/operations.xlsx", "2018-05")
    print(investment_bank("2018-05", transactions, 50))
