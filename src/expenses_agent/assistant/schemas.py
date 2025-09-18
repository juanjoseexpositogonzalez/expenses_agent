"""
Pydantic schemas for the expense assistant structured outputs.

This module defines all the data models used for parsing, classifying,
and responding to user inputs in the expense management system.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from ..models.models import Currency, PaymentMethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionType(StrEnum):
    """
    Enumeration of possible assistant actions.

    Defines the different types of operations the assistant can perform
    based on user input analysis.
    """

    CREATE_EXPENSE = "create_expense"
    LIST_EXPENSES = "list_expenses"
    UPDATE_EXPENSE = "update_expense"
    DELETE_EXPENSE = "delete_expense"
    CREATE_CATEGORY = "create_category"
    LIST_CATEGORIES = "list_categories"
    UPDATE_CATEGORY = "update_category"
    DELETE_CATEGORY = "delete_category"
    CLASSIFY_EXPENSE = "classify_expense"
    GET_SUMMARY = "get_summary"
    HELP = "help"
    UNCLEAR = "unclear"


class ConfidenceLevel(StrEnum):
    """
    Enumeration of confidence levels for classification and parsing results.

    Used to indicate how confident the assistant is about its interpretation
    of user input.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExpenseData(BaseModel):
    """
    Structured representation of expense information parsed from user input.

    Used when the assistant extracts expense details from natural language
    and needs to validate and structure the data before database storage.
    """

    amount: Optional[Decimal] = Field(None, description="The expense amount")
    currency: Optional[Currency] = Field(
        None, description="The currency of the expense"
    )
    description: Optional[str] = Field(
        None, description="Description of the expense", max_length=500
    )
    category_name: Optional[str] = Field(
        None, description="Name of the expense category"
    )
    payment_method: Optional[PaymentMethod] = Field(
        None, description="Method of payment"
    )
    expense_date: Optional[datetime] = Field(
        None, description="Date when the expense occurred"
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about the expense", max_length=1000
    )
    user_name: Optional[str] = Field(
        None, description="Name of the user creating the expense"
    )
    confidence: ConfidenceLevel = Field(
        ConfidenceLevel.MEDIUM, description="Confidence level of the parsing"
    )

    @field_validator("amount")
    def validate_amount(self, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate that amount is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("description")
    def validate_description(self, v: Optional[str]) -> Optional[str]:
        """Clean and validate description."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("expense_date")
    def validate_expense_date(self, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure expense_date has timezone info."""
        if v is not None and v.tzinfo is None:
            # Assume UTC if no timezone provided
            v = v.replace(tzinfo=timezone.utc)
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {  # type: ignore
            Decimal: str,
            datetime: lambda v: v.isoformat() if v else None,
        }


class ClassificationResult(BaseModel):
    """
    Result of expense classification by category.

    Contains the predicted category and confidence metrics for
    automatic expense categorization.
    """

    category_name: Optional[str] = Field(
        None, description="Name of the predicted category"
    )
    category_id: Optional[int] = Field(None, description="ID of the predicted category")
    confidence: ConfidenceLevel = Field(
        description="Confidence level of the classification"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Numerical confidence score between 0 and 1"
    )
    reasoning: Optional[str] = Field(
        None, description="Explanation of why this category was chosen"
    )
    alternative_categories: List[Dict[str, Union[str, float]]] = Field(  # type: ignore
        default_factory=list,
        description="Alternative categories with their confidence scores",
    )

    @field_validator("alternative_categories")
    def validate_alternatives(
        self, v: List[Dict[str, Union[str, float]]]
    ) -> List[Dict[str, Union[str, float]]]:
        """Validate alternative categories structure."""
        for alt in v:
            if not isinstance(alt, dict):  # type: ignore[misc]
                raise ValueError("Alternative categories must be dictionaries")
            if "name" not in alt or "score" not in alt:
                raise ValueError(
                    'Alternative categories must have "name" and "score" keys'
                )
            if not isinstance(alt["score"], (int, float)) or not 0 <= alt["score"] <= 1:
                raise ValueError("Alternative category scores must be between 0 and 1")
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class AssistantResponse(BaseModel):
    """
    Complete structured response from the expense assistant.

    This is the main response format that includes the action taken,
    any extracted data, and the human-readable response message.
    """

    action: ActionType = Field(description="The action determined from user input")
    success: bool = Field(description="Whether the action was completed successfully")
    message: str = Field(description="Human-readable response message", max_length=2000)

    # Optional data fields depending on the action
    expense_data: Optional[ExpenseData] = Field(
        None, description="Parsed expense data if applicable"
    )
    classification_result: Optional[ClassificationResult] = Field(
        None, description="Classification result if applicable"
    )

    # Metadata
    confidence: ConfidenceLevel = Field(
        ConfidenceLevel.MEDIUM, description="Overall confidence in the response"
    )
    requires_clarification: bool = Field(
        False, description="Whether user clarification is needed"
    )
    clarification_questions: List[str] = Field(
        default_factory=list, description="Specific questions to ask for clarification"
    )

    # Additional data for different response types
    data: Optional[Dict[str, Any]] = Field(
        None, description="Additional structured data (expenses list, categories, etc.)"
    )

    @field_validator("message")
    def validate_message(self, v: str) -> str:
        """Ensure message is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v

    @field_validator("clarification_questions")
    def validate_clarification_questions(self, v: List[str]) -> List[str]:
        """Clean clarification questions."""
        return [q.strip() for q in v if q.strip()]

    @model_validator(mode="before")
    def validate_clarification_consistency(
        self, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ensure clarification fields are consistent."""
        requires_clarification = values.get("requires_clarification", False)
        clarification_questions = values.get("clarification_questions", [])

        if requires_clarification and not clarification_questions:
            raise ValueError("If clarification is required, questions must be provided")

        if not requires_clarification and clarification_questions:
            values["requires_clarification"] = True

        return values

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {  # type: ignore
            Decimal: str,
            datetime: lambda v: v.isoformat() if v else None,
        }


class ConversationContext(BaseModel):
    """
    Context information for maintaining conversation state.

    Used to track conversation history and user preferences
    for better assistant responses.
    """

    user_name: Optional[str] = Field(None, description="Current user name")
    last_expense_data: Optional[ExpenseData] = Field(
        None, description="Last parsed expense data"
    )
    last_action: Optional[ActionType] = Field(None, description="Last action performed")
    conversation_history: List[Dict[str, str]] = Field(  # type: ignore
        default_factory=list, description="Recent conversation messages"
    )
    user_preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences (default currency, categories, etc.)",
    )

    @field_validator("conversation_history")
    def validate_conversation_history(
        self, v: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Validate conversation history structure."""
        for entry in v:
            if not isinstance(entry, dict):  # type: ignore[misc]
                raise ValueError("Conversation history entries must be dictionaries")
            if "role" not in entry or "content" not in entry:
                raise ValueError(
                    'Conversation history entries must have "role" and "content"'
                )
            if entry["role"] not in ["user", "assistant"]:
                raise ValueError('Role must be either "user" or "assistant"')
        return v

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to conversation history.

        Args:
            role: Either 'user' or 'assistant'
            content: The message content
        """
        self.conversation_history.append({"role": role, "content": content})

        # Keep only last 10 messages to prevent memory growth
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def get_recent_messages(self, count: int = 5) -> List[Dict[str, str]]:
        """
        Get recent conversation messages.

        Args:
            count: Number of recent messages to return

        Returns:
            List of recent messages
        """
        return self.conversation_history[-count:] if self.conversation_history else []

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ErrorResponse(BaseModel):
    """
    Structured error response from the assistant.

    Used when the assistant encounters errors that need to be
    communicated back to the user in a structured format.
    """

    error_type: str = Field(description="Type of error encountered")
    error_message: str = Field(description="Human-readable error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
    suggestions: List[str] = Field(
        default_factory=list, description="Suggestions for resolving the error"
    )
    retry_possible: bool = Field(
        True, description="Whether the operation can be retried"
    )

    @field_validator("error_message")
    def validate_error_message(self, v: str) -> str:
        """Ensure error message is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Error message cannot be empty")
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


# Type aliases for common response types
ExpenseResponse = AssistantResponse
CategoryResponse = AssistantResponse
SummaryResponse = AssistantResponse

# Export commonly used models
__all__ = [
    "ActionType",
    "ConfidenceLevel",
    "ExpenseData",
    "ClassificationResult",
    "AssistantResponse",
    "ConversationContext",
    "ErrorResponse",
    "ExpenseResponse",
    "CategoryResponse",
    "SummaryResponse",
]
