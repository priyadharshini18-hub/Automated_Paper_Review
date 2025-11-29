"""Pydantic models for evaluation pipeline."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class ReviewerSimilarity(BaseModel):
    """Similarity scores compared to a single reference reviewer."""
    reviewer_id: str
    
    # Summary comparison
    reference_summary: str  # Original reviewer summary
    summary_similarity: float = Field(ge=0.0, le=1.0, description="Cosine similarity of summaries")
    
    # Weakness comparison
    reference_weakness: str  # Original reviewer weakness
    weakness_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Cosine similarity of weaknesses")
    
    # Strength comparison
    reference_strength: str = ""  # Original reviewer strength
    strength_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Cosine similarity of strengths")


class WeaknessMatch(BaseModel):
    """Per-weakness matching result."""
    generated_weakness: str
    best_matching_reviewer: str
    best_match_score: float = Field(ge=0.0, le=1.0)
    matched_reference_weakness: str


class StrengthMatch(BaseModel):
    """Per-strength matching result."""
    generated_strength: str
    best_matching_reviewer: str
    best_match_score: float = Field(ge=0.0, le=1.0)
    matched_reference_strength: str


class PaperResult(BaseModel):
    """Evaluation result for a single paper."""
    paper_id: str
    paper_file: str
    paper_type: str  # "accepted" or "rejected"
    
    # Generated content
    executive_summary: str
    generated_weaknesses: List[str] = []
    generated_strengths: List[str] = []
    
    # Similarity with each reference reviewer
    reviewer_similarities: List[ReviewerSimilarity] = []
    
    # Aggregate summary metrics
    avg_summary_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    max_summary_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    min_summary_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Aggregate weakness metrics (original - comparing all weaknesses as one)
    avg_weakness_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    max_weakness_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    min_weakness_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Enhanced weakness metrics
    per_weakness_matches: List[WeaknessMatch] = []  # Per-weakness best matches
    avg_best_weakness_match: float = Field(default=0.0, ge=0.0, le=1.0, 
        description="Average of best-match similarity for each generated weakness")
    weakness_coverage_score: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Fraction of reviewers whose weaknesses are covered (sim > threshold)")
    aggregate_weakness_similarity: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Similarity of generated weaknesses to all reviewer weaknesses combined")
    
    # Aggregate strength metrics (original - comparing all strengths as one)
    avg_strength_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    max_strength_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    min_strength_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Enhanced strength metrics
    per_strength_matches: List[StrengthMatch] = []  # Per-strength best matches
    avg_best_strength_match: float = Field(default=0.0, ge=0.0, le=1.0, 
        description="Average of best-match similarity for each generated strength")
    strength_coverage_score: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Fraction of reviewers whose strengths are covered (sim > threshold)")
    aggregate_strength_similarity: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Similarity of generated strengths to all reviewer strengths combined")


class EvaluationSummary(BaseModel):
    """Overall evaluation metrics across all papers."""
    timestamp: datetime = Field(default_factory=datetime.now)
    total_papers: int
    
    # Summary similarity metrics
    overall_avg_summary_similarity: float
    overall_std_summary_similarity: float
    accepted_avg_summary_similarity: float
    rejected_avg_summary_similarity: float
    
    # Weakness similarity metrics (original)
    overall_avg_weakness_similarity: float
    overall_std_weakness_similarity: float
    accepted_avg_weakness_similarity: float
    rejected_avg_weakness_similarity: float
    
    # Enhanced weakness metrics (aggregated across all papers)
    overall_avg_best_weakness_match: float = Field(default=0.0,
        description="Average best-match similarity across all papers")
    overall_avg_weakness_coverage: float = Field(default=0.0,
        description="Average reviewer coverage across all papers")
    overall_avg_aggregate_weakness_similarity: float = Field(default=0.0,
        description="Average aggregate similarity across all papers")
    
    # Strength similarity metrics (original)
    overall_avg_strength_similarity: float = Field(default=0.0)
    overall_std_strength_similarity: float = Field(default=0.0)
    accepted_avg_strength_similarity: float = Field(default=0.0)
    rejected_avg_strength_similarity: float = Field(default=0.0)
    
    # Enhanced strength metrics (aggregated across all papers)
    overall_avg_best_strength_match: float = Field(default=0.0,
        description="Average best-match similarity across all papers")
    overall_avg_strength_coverage: float = Field(default=0.0,
        description="Average reviewer coverage across all papers")
    overall_avg_aggregate_strength_similarity: float = Field(default=0.0,
        description="Average aggregate similarity across all papers")
    
    # Per-paper results
    paper_results: List[PaperResult]


class FinalReport(BaseModel):
    """Pydantic model for final_report.json validation."""
    title: str
    authors: Optional[str] = None
    date_reviewed: str
    executive_summary: str
    problem_statement: str
    research_objectives: List[str]
    methodology: str
    key_results: str
    metrics: List[Dict[str, str]] = []
    strengths: List[str]
    weaknesses: List[str]
    conclusions: str
    future_work: List[str]
