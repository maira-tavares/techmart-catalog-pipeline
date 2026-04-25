# utils/models.py
# Pydantic models for data validation in the TechMart pipeline.
# These models ensure LLM outputs have the correct structure and types
# before being written to Delta tables.

from pydantic import BaseModel, Field
from typing import Optional, List


class ProductExtraction(BaseModel):
    """
    Validates the output of the LLM extraction step.
    Ensures name, brand and sub_category are present and are strings.
    """
    name        : str = Field(..., description="Clean product name")
    brand       : str = Field(..., description="Brand name")
    sub_category: str = Field(..., description="Product sub-category")


class JudgeResult(BaseModel):
    """
    Validates the output of the LLM Judge step.
    Ensures approved is a boolean and reason is a string.
    """
    approved: bool = Field(..., description="Whether the extraction passed taxonomy validation")
    reason  : str  = Field(default="", description="Reason for rejection if not approved")


class ProductState(BaseModel):
    """
    Represents the full state of a product through the pipeline.
    Tracks every field from raw input to final validated output.
    """
    product_id   : int
    description  : str
    name         : Optional[str]  = None
    brand        : Optional[str]  = None
    sub_category : Optional[str]  = None
    judge_approved: Optional[bool] = None
    judge_reason  : Optional[str]  = None
    llm_status    : Optional[str]  = None
    input_tokens  : Optional[int]  = None
    output_tokens : Optional[int]  = None
    latency_seconds: Optional[float] = None
    prompt_version: Optional[str]  = None