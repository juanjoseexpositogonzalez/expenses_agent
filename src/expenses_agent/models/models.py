# models.py
"""
Defines the data models for the expenses agent application, including Category and Expense classes.
These models are used for representing expense categories and individual expense records.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Optional, Self

from decouple import config
from sqlmodel import Field, SQLModel, create_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PaymentMethod(StrEnum):
    """
    Enumeration of possible payment methods for expenses.
    Inherits from StrEnum to provide string values for each payment method.
    Values:
        CREDIT_CARD: Payment made by credit card.
        DEBIT_CARD: Payment made by debit card.
        CASH: Payment made in cash.
        BANK_TRANSFER: Payment made by bank transfer.
        MOBILE_PAYMENT: Payment made using a mobile payment system.
        CHECK: Payment made by check.
        OTHER: Any other payment method not listed above.
    """

    CREDIT_CARD = "Credit Card"
    DEBIT_CARD = "Debit Card"
    CASH = "Cash"
    BANK_TRANSFER = "Bank Transfer"
    MOBILE_PAYMENT = "Mobile Payment"
    CHECK = "Check"
    OTHER = "Other"


class Currency(StrEnum):
    """
    Enumeration of supported currencies.
    Inherits from StrEnum to provide string values for each currency.
    Values:
        USD: United States Dollar.
        EUR: Euro.
        GBP: British Pound Sterling.
        JPY: Japanese Yen.
        AUD: Australian Dollar.
        CAD: Canadian Dollar.
        CHF: Swiss Franc.
        CNY: Chinese Yuan.
        SEK: Swedish Krona.
        NZD: New Zealand Dollar.
    """

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    AUD = "AUD"
    CAD = "CAD"
    CHF = "CHF"
    CNY = "CNY"
    SEK = "SEK"
    NZD = "NZD"


class Category(SQLModel, table=True):
    """
    Represents an expense category.
    Attributes:
        name (str): The name of the category.
        description (str, optional): A description of the category.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    color_code: str
    is_active: bool = True
    created_at: Optional[datetime] = Field(default=datetime.now(timezone.utc))

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class Expense(SQLModel, table=True):
    """
    Represents an expense record.
    Attributes:
        amount (float): The amount of the expense.
        category (Category): The category associated with the expense.
        date (datetime): The date of the expense.
        description (str, optional): A description of the expense.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    user_name: str
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    amount: Decimal
    currency: Currency
    description: str
    expense_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: Optional[datetime] = Field(default=datetime.now(timezone.utc))
    payment_method: PaymentMethod = Field(default=PaymentMethod.OTHER)
    notes: str

    def __init__(self, **kwargs: Any) -> Any:
        super().__init__(**kwargs)
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    @classmethod
    def create_expense(
        cls,
        user_name: str,
        category_id: Optional[int],
        amount: Decimal,
        currency: Currency,
        description: str,
        expense_date: Optional[datetime] = None,
        payment_method: PaymentMethod = PaymentMethod.OTHER,
        notes: str = "",
    ) -> Self:
        """
        Factory method to create a new Expense instance.
        Args:
            user_name (str): The name of the user associated with the expense.
            category_id (Optional[int]): The ID of the category associated with the expense.
            amount (Decimal): The amount of the expense.
            currency (Currency): The currency of the expense.
            description (str): A description of the expense.
            expense_date (Optional[datetime]): The date of the expense. Defaults to now if not provided.
            payment_method (PaymentMethod): The method of payment for the expense. Defaults to OTHER.
        Returns:
            Expense: A new instance of the Expense class.
        """
        if expense_date is None:
            expense_date = datetime.now(timezone.utc)
        return cls(
            user_name=user_name,
            category_id=category_id,
            amount=amount,
            currency=currency,
            description=description,
            expense_date=expense_date,
            payment_method=payment_method,
            notes=notes,
        )


def create_db_and_tables() -> None:  # pragma: no cover
    """
    Creates the database and tables based on the defined SQLModel models.
    """
    database_url = config("DATABASE_URL", default="sqlite:///expenses_agent.db")  # type: ignore
    engine = create_engine(database_url, echo=False)  # type: ignore
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":  # pragma: no cover
    create_db_and_tables()
    logger.info("Database and tables created successfully.")
