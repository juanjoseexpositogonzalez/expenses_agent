"""
Manual expense recording workflow for the expenses agent application.

This module provides the core workflow for manually recording and classifying expenses
through a simple console interface.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from expenses_agent.models.database import (
    CategoryRepository,
    DatabaseManager,
    ExpenseRepository,
)
from expenses_agent.models.models import Category, Currency, Expense, PaymentMethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkflowUI:
    """
    Simple console interface for expense workflow.

    Provides methods for user interaction through console prompts
    and displays formatted information.
    """

    @staticmethod
    def display_header(title: str) -> None:
        """
        Display a formatted header.

        Args:
            title: The title to display.
        """
        print(f"\n{'='*50}")
        print(f" {title}")
        print(f"{'='*50}")

    @staticmethod
    def display_categories(categories: List[Category]) -> None:
        """
        Display available categories in a formatted menu.

        Args:
            categories: List of categories to display.
        """
        print("\nAvailable Categories:")
        print("-" * 30)
        for i, category in enumerate(categories, 1):
            status = "✓" if category.is_active else "✗"
            print(f"{i:2d}. {status} {category.name} - {category.description}")
        print(f"{len(categories) + 1:2d}. [No Category]")

    @staticmethod
    def display_currencies() -> None:
        """Display available currencies."""
        print("\nAvailable Currencies:")
        print("-" * 30)
        currencies = list(Currency)
        for i, currency in enumerate(currencies, 1):
            print(f"{i:2d}. {currency.value}")

    @staticmethod
    def display_payment_methods() -> None:
        """Display available payment methods."""
        print("\nPayment Methods:")
        print("-" * 30)
        methods = list(PaymentMethod)
        for i, method in enumerate(methods, 1):
            print(f"{i:2d}. {method.value}")

    @staticmethod
    def prompt_for_input(prompt: str, required: bool = True) -> str:
        """
        Prompt user for input with validation.

        Args:
            prompt: The prompt message to display.
            required: Whether the input is required.

        Returns:
            str: The user input.
        """
        while True:
            user_input = input(f"{prompt}: ").strip()
            if user_input or not required:
                return user_input
            print("This field is required. Please enter a value.")

    @staticmethod
    def confirm_expense_details(
        expense_data: Dict[str, Any], category_name: Optional[str]
    ) -> bool:
        """
        Display expense details and ask for confirmation.

        Args:
            expense_data: Dictionary containing expense information.
            category_name: Name of the selected category.

        Returns:
            bool: True if user confirms, False otherwise.
        """
        print("\n" + "=" * 40)
        print(" EXPENSE SUMMARY")
        print("=" * 40)
        print(f"User: {expense_data['user_name']}")
        print(f"Amount: {expense_data['amount']} {expense_data['currency'].value}")
        print(f"Description: {expense_data['description']}")
        print(f"Category: {category_name or 'No Category'}")
        print(f"Payment Method: {expense_data['payment_method'].value}")
        print(f"Date: {expense_data['expense_date'].strftime('%Y-%m-%d %H:%M')}")
        if expense_data["notes"]:
            print(f"Notes: {expense_data['notes']}")
        print("=" * 40)

        while True:
            confirm = input("Save this expense? (y/n): ").strip().lower()
            if confirm in ["y", "yes"]:
                return True
            elif confirm in ["n", "no"]:
                return False
            print("Please enter 'y' for yes or 'n' for no.")


class ExpenseWorkflow:
    """
    Main workflow for manual expense recording.

    Handles the complete process of expense input, validation,
    classification, and storage.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        """
        Initialize expense workflow.

        Args:
            db_manager: Database manager instance. If None, creates a new one.
        """
        self.db_manager = db_manager or DatabaseManager()
        self.category_repo = CategoryRepository(self.db_manager)
        self.expense_repo = ExpenseRepository(self.db_manager)
        self.ui = WorkflowUI()

    def record_expense(self, user_name: str) -> Optional[Expense]:
        """
        Complete workflow to record a new expense.

        Args:
            user_name: Name of the user recording the expense.

        Returns:
            Optional[Expense]: Created expense if successful, None if cancelled.
        """
        try:
            self.ui.display_header("EXPENSE RECORDING")

            # Get expense data from user
            expense_data = self._get_expense_data(user_name)
            if not expense_data:
                print("Expense recording cancelled.")
                return None

            # Get category selection
            category = self._get_category_selection()
            if category:
                expense_data["category_id"] = category.id
                category_name = category.name
            else:
                expense_data["category_id"] = None
                category_name = None

            # Confirm before saving
            if not self.ui.confirm_expense_details(expense_data, category_name):
                print("Expense recording cancelled.")
                return None

            # Create expense
            expense = self.expense_repo.create_expense(expense_data)
            print(f"\n✓ Expense recorded successfully! (ID: {expense.id})")
            logger.info(
                "Expense recorded: %s - %d %s",
                expense.description,
                expense.amount,
                expense.currency,
            )

            return expense

        except Exception as e:
            logger.error("Error recording expense: %s", e)
            print(f"Error: {e}")
            return None

    def _get_expense_data(self, user_name: str) -> Optional[Dict[str, Any]]:
        """
        Collect expense data from user input.

        Args:
            user_name: Name of the user recording the expense.

        Returns:
            Optional[Dict[str, Any]]: Expense data dictionary or None if cancelled.
        """
        try:
            # Get amount
            amount = self._get_amount_input()
            if amount is None:
                return None

            # Get currency
            currency = self._get_currency_selection()
            if currency is None:
                return None

            # Get description
            description = self.ui.prompt_for_input("Description")

            # Get payment method
            payment_method = self._get_payment_method_selection()
            if payment_method is None:
                return None

            # Get notes (optional)
            notes = self.ui.prompt_for_input("Notes (optional)", required=False)

            # Get date (default to now)
            expense_date = self._get_date_input()

            return {
                "user_name": user_name,
                "amount": amount,
                "currency": currency,
                "description": description,
                "payment_method": payment_method,
                "notes": notes,
                "expense_date": expense_date,
            }

        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return None

    def _get_amount_input(self) -> Optional[Decimal]:
        """
        Get and validate amount input from user.

        Returns:
            Optional[Decimal]: Valid amount or None if cancelled.
        """
        while True:
            try:
                amount_str = self.ui.prompt_for_input("Amount")
                if not amount_str:
                    return None

                amount = Decimal(amount_str)
                if amount <= 0:
                    print("Amount must be greater than 0.")
                    continue

                return amount

            except InvalidOperation:
                print("Invalid amount format. Please enter a valid number.")
            except KeyboardInterrupt:
                return None

    def _get_currency_selection(self) -> Optional[Currency]:
        """
        Get currency selection from user.

        Returns:
            Optional[Currency]: Selected currency or None if cancelled.
        """
        currencies = list(Currency)

        while True:
            try:
                self.ui.display_currencies()
                choice = self.ui.prompt_for_input("Select currency (number)")

                if not choice:
                    return None

                choice_num = int(choice)
                if 1 <= choice_num <= len(currencies):
                    return currencies[choice_num - 1]
                else:
                    print(f"Please select a number between 1 and {len(currencies)}.")

            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                return None

    def _get_payment_method_selection(self) -> Optional[PaymentMethod]:
        """
        Get payment method selection from user.

        Returns:
            Optional[PaymentMethod]: Selected payment method or None if cancelled.
        """
        methods = list(PaymentMethod)

        while True:
            try:
                self.ui.display_payment_methods()
                choice = self.ui.prompt_for_input("Select payment method (number)")

                if not choice:
                    return None

                choice_num = int(choice)
                if 1 <= choice_num <= len(methods):
                    return methods[choice_num - 1]
                else:
                    print(f"Please select a number between 1 and {len(methods)}.")

            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                return None

    def _get_category_selection(self) -> Optional[Category]:
        """
        Get category selection from user.

        Returns:
            Optional[Category]: Selected category or None for no category.
        """
        categories = self.category_repo.get_all_categories(active_only=True)

        if not categories:
            print("No categories available. Expense will be recorded without category.")
            return None

        while True:
            try:
                self.ui.display_categories(categories)
                choice = self.ui.prompt_for_input("Select category (number)")

                if not choice:
                    return None

                choice_num = int(choice)
                if 1 <= choice_num <= len(categories):
                    return categories[choice_num - 1]
                elif choice_num == len(categories) + 1:
                    return None  # No category selected
                else:
                    print(
                        f"Please select a number between 1 and {len(categories) + 1}."
                    )

            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                return None

    def _get_date_input(self) -> datetime:
        """
        Get expense date from user (defaults to current time).

        Returns:
            datetime: Expense date.
        """
        # For Week 1, we'll default to current time
        # This can be extended later to allow custom date input
        return datetime.now(timezone.utc)

    def display_recent_expenses(self, user_name: str, limit: int = 5) -> None:
        """
        Display recent expenses for a user.

        Args:
            user_name: Name of the user.
            limit: Maximum number of expenses to display.
        """
        expenses = self.expense_repo.get_expenses_by_user(user_name)

        if not expenses:
            print(f"\nNo expenses found for user: {user_name}")
            return

        # Sort by creation date (most recent first)
        recent_expenses = sorted(  # type: ignore
            expenses,
            key=lambda x: x.created_at,  # type: ignore
            reverse=True,  # type: ignore
        )[  # type: ignore
            :limit
        ]  # type: ignore

        print(f"\nRecent Expenses for {user_name}:")
        print("-" * 60)
        for expense in recent_expenses:  # type: ignore
            category_name = "No Category"
            if expense.category_id:
                category = self.category_repo.get_category_by_id(expense.category_id)  # type: ignore
                if category:
                    category_name = category.name

            print(
                f"• {expense.description[:30]:<30} {expense.amount:>8} {expense.currency.value} [{category_name}]"
            )


def main() -> None:
    """
    Main function to run the expense recording workflow.

    This function can be used for testing or as a standalone script.
    """
    try:
        # Initialize database
        db_manager = DatabaseManager()
        db_manager.create_tables()

        # Create workflow
        workflow = ExpenseWorkflow(db_manager)

        # Get user name
        print("Welcome to Expense Recording System!")
        user_name = input("Enter your name: ").strip()

        if not user_name:
            print("User name is required.")
            return

        # Main loop
        while True:
            print(f"\n--- Expense Recording for {user_name} ---")
            print("1. Record new expense")
            print("2. View recent expenses")
            print("3. Exit")

            choice = input("Select option (1-3): ").strip()

            if choice == "1":
                workflow.record_expense(user_name)
            elif choice == "2":
                workflow.display_recent_expenses(user_name)
            elif choice == "3":
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please select 1, 2, or 3.")

    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        logger.error("Unexpected error in main: %s", e)
        print(f"An error occurred: {e}")


if __name__ == "__main__":  # pragma: no cover
    main()
