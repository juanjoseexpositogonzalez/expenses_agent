"""
Database CRUD operations for the expenses agent application.

This module provides repository classes for managing Category and Expense data
with proper session handling and error management.
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from decouple import config
from sqlmodel import Session, SQLModel, create_engine, select

from .models import Category, Expense

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and session lifecycle.

    Provides centralized database configuration and session management
    for repository classes.
    """

    _instance: Optional["DatabaseManager"] = None
    _engine = None

    def __new__(cls) -> "DatabaseManager":
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize database manager with engine configuration."""
        if self._engine is None:
            database_url: str = config(  # type: ignore
                "DATABASE_URL", default="sqlite:///expenses_agent.db"
            )  # type: ignore
            self._engine = create_engine(database_url, echo=False)  # type: ignore
            logger.info("Database engine initialized with URL: %s", database_url)

    @property
    def engine(self):
        """Get the database engine instance."""
        return self._engine

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.

        Yields:
            Session: SQLModel session for database operations.

        Example:
            with db_manager.get_session() as session:
                # Perform database operations
                pass
        """
        session = Session(self._engine)
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Database session error: %s", e)
            raise
        finally:
            session.close()

    def create_tables(self) -> None:
        """Create all database tables if they don't exist."""
        SQLModel.metadata.create_all(self._engine)  # type: ignore
        logger.info("Database tables created successfully")


class CategoryRepository:
    """
    Repository for Category CRUD operations.

    Provides methods to create, read, update, and delete category records
    with proper error handling and logging.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        """
        Initialize category repository.

        Args:
            db_manager: Database manager instance. If None, creates a new one.
        """
        self.db_manager = db_manager or DatabaseManager()

    def create_category(self, category_data: Dict[str, Any]) -> Category:
        """
        Create a new category.

        Args:
            category_data: Dictionary containing category information.
                          Must include 'name', 'description', 'color_code'.
                          Optional: 'is_active' (defaults to True).

        Returns:
            Category: The created category instance.

        Raises:
            ValueError: If required fields are missing.
            Exception: If database operation fails.
        """
        required_fields = {"name", "description", "color_code"}
        if not required_fields.issubset(category_data.keys()):
            missing_fields = required_fields - set(category_data.keys())
            raise ValueError(f"Missing required fields: {missing_fields}")

        with self.db_manager.get_session() as session:
            category = Category(**category_data)
            session.add(category)
            session.flush()  # Get the ID without committing
            session.refresh(category)
            logger.info("Created category: %s  (ID: %d)", category.name, category.id)
            return category

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """
        Retrieve a category by its ID.

        Args:
            category_id: The unique identifier of the category.

        Returns:
            Optional[Category]: The category if found, None otherwise.
        """
        with self.db_manager.get_session() as session:
            statement = select(Category).where(Category.id == category_id)
            category = session.exec(statement).first()
            if category:
                logger.debug(
                    "Retrieved category: %s (ID: %d)", category.name, category_id
                )
            return category

    def get_all_categories(self, active_only: bool = True) -> List[Category]:
        """
        Retrieve all categories.

        Args:
            active_only: If True, only return active categories.
                        If False, return all categories.

        Returns:
            List[Category]: List of category instances.
        """
        with self.db_manager.get_session() as session:
            statement = select(Category)
            if active_only:
                statement = statement.where(Category.is_active is True)

            categories = session.exec(statement).all()
            logger.debug(
                "Retrieved %d categories (active_only=%s)", len(categories), active_only
            )
            return list(categories)

    def update_category(
        self, category_id: int, updates: Dict[str, Any]
    ) -> Optional[Category]:
        """
        Update an existing category.

        Args:
            category_id: The unique identifier of the category.
            updates: Dictionary containing fields to update.

        Returns:
            Optional[Category]: The updated category if found, None otherwise.
        """
        with self.db_manager.get_session() as session:
            statement = select(Category).where(Category.id == category_id)
            category = session.exec(statement).first()

            if category:
                for field, value in updates.items():
                    if hasattr(category, field):
                        setattr(category, field, value)

                session.add(category)
                session.flush()
                session.refresh(category)
                logger.info("Updated category: %s (ID: %d)", category.name, category_id)
                return category

            logger.warning("Category not found for update: ID %d", category_id)
            return None

    def delete_category(self, category_id: int) -> bool:
        """
        Delete a category by its ID.

        Args:
            category_id: The unique identifier of the category.

        Returns:
            bool: True if category was deleted, False if not found.
        """
        with self.db_manager.get_session() as session:
            statement = select(Category).where(Category.id == category_id)
            category = session.exec(statement).first()

            if category:
                session.delete(category)
                logger.info("Deleted category: %s (ID: %d)", category.name, category_id)
                return True

            logger.warning("Category not found for deletion: ID %d", category_id)
            return False


class ExpenseRepository:
    """
    Repository for Expense CRUD operations.

    Provides methods to create, read, update, and delete expense records
    with proper error handling and logging.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        """
        Initialize expense repository.

        Args:
            db_manager: Database manager instance. If None, creates a new one.
        """
        self.db_manager = db_manager or DatabaseManager()

    def create_expense(self, expense_data: Dict[str, Any]) -> Expense:
        """
        Create a new expense.

        Args:
            expense_data: Dictionary containing expense information.
                         Must include required fields from Expense model.

        Returns:
            Expense: The created expense instance.

        Raises:
            ValueError: If required fields are missing.
            Exception: If database operation fails.
        """
        required_fields = {"user_name", "amount", "currency", "description", "notes"}
        if not required_fields.issubset(expense_data.keys()):
            missing_fields = required_fields - set(expense_data.keys())
            raise ValueError(f"Missing required fields: {missing_fields}")

        with self.db_manager.get_session() as session:
            expense = Expense(**expense_data)
            session.add(expense)
            session.flush()
            session.refresh(expense)
            logger.info(
                "Created expense: %s - %s%s",
                expense.description,
                expense.amount,
                expense.currency,
            )
            return expense

    def get_expense_by_id(self, expense_id: int) -> Optional[Expense]:
        """
        Retrieve an expense by its ID.

        Args:
            expense_id: The unique identifier of the expense.

        Returns:
            Optional[Expense]: The expense if found, None otherwise.
        """
        with self.db_manager.get_session() as session:
            statement = select(Expense).where(Expense.id == expense_id)
            expense = session.exec(statement).first()
            if expense:
                logger.debug(
                    "Retrieved expense: %s (ID: %d)", expense.description, expense_id
                )
            return expense

    def get_expenses_by_user(self, user_name: str) -> List[Expense]:
        """
        Retrieve all expenses for a specific user.

        Args:
            user_name: The name of the user.

        Returns:
            List[Expense]: List of expense instances for the user.
        """
        with self.db_manager.get_session() as session:
            statement = select(Expense).where(Expense.user_name == user_name)
            expenses = session.exec(statement).all()
            logger.debug("Retrieved %d expenses for user: %s", len(expenses), user_name)
            return list(expenses)

    def get_expenses_by_category(self, category_id: int) -> List[Expense]:
        """
        Retrieve all expenses for a specific category.

        Args:
            category_id: The unique identifier of the category.

        Returns:
            List[Expense]: List of expense instances for the category.
        """
        with self.db_manager.get_session() as session:
            statement = select(Expense).where(Expense.category_id == category_id)
            expenses = session.exec(statement).all()
            logger.debug(
                "Retrieved %d expenses for category ID: %d", len(expenses), category_id
            )
            return list(expenses)

    def update_expense(
        self, expense_id: int, updates: Dict[str, Any]
    ) -> Optional[Expense]:
        """
        Update an existing expense.

        Args:
            expense_id: The unique identifier of the expense.
            updates: Dictionary containing fields to update.

        Returns:
            Optional[Expense]: The updated expense if found, None otherwise.
        """
        with self.db_manager.get_session() as session:
            statement = select(Expense).where(Expense.id == expense_id)
            expense = session.exec(statement).first()

            if expense:
                for field, value in updates.items():
                    if hasattr(expense, field):
                        setattr(expense, field, value)

                session.add(expense)
                session.flush()
                session.refresh(expense)
                logger.info(
                    "Updated expense: %s (ID: %d)", expense.description, expense_id
                )
                return expense

            logger.warning("Expense not found for update: ID %d", expense_id)
            return None

    def delete_expense(self, expense_id: int) -> bool:
        """
        Delete an expense by its ID.

        Args:
            expense_id: The unique identifier of the expense.

        Returns:
            bool: True if expense was deleted, False if not found.
        """
        with self.db_manager.get_session() as session:
            statement = select(Expense).where(Expense.id == expense_id)
            expense = session.exec(statement).first()

            if expense:
                session.delete(expense)
                logger.info(
                    "Deleted expense: %s (ID: %d)",
                    expense.description,
                    expense_id,
                )
                return True

            logger.warning("Expense not found for deletion: ID %d", expense_id)
            return False


# Convenience function for initialization
def initialize_database() -> DatabaseManager:
    """
    Initialize database and create tables.

    Returns:
        DatabaseManager: Configured database manager instance.
    """
    db_manager = DatabaseManager()
    db_manager.create_tables()
    return db_manager


if __name__ == "__main__":  # pragma: no cover
    # Example usage and testing
    main_db_manager = initialize_database()

    # Test category operations
    category_repo = CategoryRepository(main_db_manager)
    expense_repo = ExpenseRepository(main_db_manager)

    logger.info("Database CRUD module initialized successfully")
