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
    
    judge_taxonomy : The Judge's own classification of the product.
                     Must be one value from the approved taxonomy.
    judge_approved : True if judge_taxonomy matches extracted sub_category.
                     False if the Judge disagrees with the extractor.
    reason         : Explanation when judge_approved is False.
    """
    judge_taxonomy : str  = Field(..., description="Judge's own sub-category classification")
    judge_approved : bool = Field(..., description="True if judge agrees with extractor")
    reason         : str  = Field(default="", description="Reason for disagreement")

# class ProductState(BaseModel):
#     """
#     Represents the full state of a product through the pipeline.
#     Tracks every field from raw input to final validated output.
#     """
#     product_id   : int
#     description  : str
#     name         : Optional[str]  = None
#     brand        : Optional[str]  = None
#     sub_category : Optional[str]  = None
#     judge_approved: Optional[bool] = None
#     judge_reason  : Optional[str]  = None
#     llm_status    : Optional[str]  = None
#     input_tokens  : Optional[int]  = None
#     output_tokens : Optional[int]  = None
#     latency_seconds: Optional[float] = None
#     prompt_version: Optional[str]  = None