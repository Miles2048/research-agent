import os
from pydantic import BaseModel, Field
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig


class Configuration(BaseModel):
    """The configuration for the planning agent."""

    evaluation_model: str = Field(
        default="gpt-4o-mini",
        metadata={
            "description": "The name of the OpenAI language model to use for requirement evaluation."
        },
    )

    generation_model: str = Field(
        default="gpt-4o",
        metadata={
            "description": "The name of the OpenAI language model to use for JSON generation."
        },
    )

    max_planning_loops: int = Field(
        default=5,
        metadata={
            "description": "The maximum number of planning iteration loops."
        },
    )

    max_clarification_questions: int = Field(
        default=3,
        metadata={
            "description": "The maximum number of clarification questions to generate."
        },
    )

    json_validation_retries: int = Field(
        default=2,
        metadata={
            "description": "The maximum number of JSON validation retries."
        },
    )

    llm_timeout: int = Field(
        default=30,
        metadata={
            "description": "The timeout in seconds for LLM API calls."
        },
    )

    temperature: float = Field(
        default=0.3,
        metadata={
            "description": "The temperature parameter for LLM generation."
        },
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        # Get raw values from environment or config
        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }

        # Filter out None values
        values = {k: v for k, v in raw_values.items() if v is not None}

        return cls(**values)
