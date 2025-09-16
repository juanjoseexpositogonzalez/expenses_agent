import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.expenses_agent.models.models import Category, Currency, Expense, PaymentMethod

engine = create_engine("sqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


def test_create_category_without_created_at():
    with Session(engine) as session:
        category = Category(
            name="Test Category",
            description="Test category description",
            color_code="#FFFFFF",
        )
        session.add(category)
        session.commit()
        session.refresh(category)

        assert category.id is not None
        assert category.name == "Test Category"
        assert category.description == "Test category description"
        assert category.color_code == "#FFFFFF"
        assert isinstance(category.created_at, datetime.datetime)


def test_create_category():
    with Session(engine) as session:
        category = Category(
            name="Test Category",
            description="Test category description",
            color_code="#FFFFFF",
        )
        session.add(category)
        session.commit()
        session.refresh(category)

        assert category.id is not None
        assert category.name == "Test Category"
        assert category.description == "Test category description"
        assert category.color_code == "#FFFFFF"


def test_create_expense():
    with Session(engine) as session:
        category = Category(
            name="Test Category",
            description="Test category description",
            color_code="#FFFFFF",
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        expense = Expense.create_expense(
            user_name="test_user",
            category_id=category.id,
            amount=Decimal("100.00"),
            currency=Currency.USD,
            description="Test expense",
            notes="Test notes",
        )
        session.add(expense)
        session.commit()
        session.refresh(expense)

        assert expense.id is not None
        assert expense.user_name == "test_user"
        assert expense.amount == Decimal("100.00")
        assert expense.currency == Currency.USD
        assert expense.description == "Test expense"
        assert expense.payment_method == PaymentMethod.OTHER
        assert isinstance(expense.expense_date, datetime.datetime)
        assert isinstance(expense.created_at, datetime.datetime)


def test_category_init_sets_created_at():
    category = Category(
        name="InitTest", description="Init test desc", color_code="#000000"
    )
    assert category.name == "InitTest"
    assert category.description == "Init test desc"
    assert category.color_code == "#000000"
    assert isinstance(category.created_at, datetime.datetime)


def test_expense_init_sets_defaults():
    expense = Expense(
        user_name="init_user",
        category_id=1,
        amount=Decimal("42.00"),
        currency=Currency.EUR,
        description="Init expense",
        notes="Init notes",
    )
    assert expense.user_name == "init_user"
    assert expense.category_id == 1
    assert expense.amount == Decimal("42.00")
    assert expense.currency == Currency.EUR
    assert expense.description == "Init expense"
    assert expense.notes == "Init notes"
    assert isinstance(expense.created_at, datetime.datetime)
    assert isinstance(expense.expense_date, datetime.datetime)
    assert expense.payment_method == PaymentMethod.OTHER
