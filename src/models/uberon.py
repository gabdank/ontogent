"""
Pydantic models for UBERON ontology terms and search results.

These models define the structure of data used throughout the application
and ensure type consistency.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class UberonTerm(BaseModel):
    """Model representing a term from the UBERON ontology."""
    
    id: str = Field(..., description="UBERON ID (e.g., 'UBERON:0000948')")
    label: str = Field(..., description="Human-readable label for the term")
    definition: Optional[str] = Field(None, description="Definition of the term")
    synonyms: List[str] = Field(default_factory=list, description="Alternative names for the term")
    parent_ids: List[str] = Field(default_factory=list, description="IDs of parent terms")
    url: Optional[str] = Field(None, description="URL to the term's page")
    
    def __str__(self) -> str:
        """String representation of the UBERON term."""
        return f"{self.id}: {self.label}"


class SearchQuery(BaseModel):
    """Model representing a search query for UBERON terms."""
    
    query: str = Field(..., description="Search query string")
    max_results: int = Field(10, description="Maximum number of results to return")
    include_definitions: bool = Field(True, description="Whether to include definitions in results")
    include_synonyms: bool = Field(True, description="Whether to include synonyms in results")


class SearchResult(BaseModel):
    """Model representing search results for UBERON terms."""
    
    query: str = Field(..., description="Original search query")
    matches: List[UberonTerm] = Field(default_factory=list, description="Matching UBERON terms")
    total_matches: int = Field(0, description="Total number of matches found")
    best_match: Optional[UberonTerm] = Field(None, description="Best matching term")
    confidence: Optional[float] = Field(None, description="Confidence score for the best match (0-1)")
    reasoning: Optional[str] = Field(None, description="Reasoning for the best match selection")
    
    def __str__(self) -> str:
        """String representation of the search results."""
        if self.best_match:
            return f"Best match: {self.best_match}\nConfidence: {self.confidence:.2f}\nReasoning: {self.reasoning}"
        return f"No matches found for query: {self.query}" 