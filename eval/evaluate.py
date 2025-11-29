"""Evaluation script to compute semantic similarity between generated and reference summaries/weaknesses."""

import sys
from pathlib import Path
import json
import re
from datetime import datetime

import numpy as np
import pandas as pd

# Try to import sentence-transformers for semantic similarity
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️  sentence-transformers not installed. Install with: pip install sentence-transformers")

from models import PaperResult, ReviewerSimilarity, EvaluationSummary, WeaknessMatch, StrengthMatch

# Constants
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"
ACCEPTED_REF_PATH = PROJECT_ROOT / "eval" / "accepted_reference.csv"
REJECTED_REF_PATH = PROJECT_ROOT / "eval" / "rejected_reference.csv"

# Number of reviewers per paper
NUM_REVIEWERS = 4

# Threshold for considering a weakness as "covered"
COVERAGE_THRESHOLD = 0.5


def load_reference_data() -> dict:
    """
    Load reference reviewer summaries, weaknesses, and strengths from CSV files.
    
    Returns:
        dict mapping paper_name -> {
            'summaries': [list of reviewer summaries],
            'weaknesses': [list of reviewer weaknesses],
            'strengths': [list of reviewer strengths]
        }
    """
    references = {}
    
    # Load accepted papers reference
    if ACCEPTED_REF_PATH.exists():
        df_accepted = pd.read_csv(ACCEPTED_REF_PATH)
        for i in range(len(df_accepted)):
            paper_name = f"accepted_paper_{i+1}"
            summaries = []
            weaknesses = []
            strengths = []
            for j in range(1, NUM_REVIEWERS + 1):
                # Load summaries
                summary_col = f"reviewer_{j}_summary"
                if summary_col in df_accepted.columns:
                    summary = df_accepted.iloc[i][summary_col]
                    if pd.notna(summary):
                        summaries.append(str(summary))
                    else:
                        summaries.append("")
                
                # Load weaknesses
                weakness_col = f"reviewer_{j}_weakness"
                if weakness_col in df_accepted.columns:
                    weakness = df_accepted.iloc[i][weakness_col]
                    if pd.notna(weakness):
                        weaknesses.append(str(weakness))
                    else:
                        weaknesses.append("")
                
                # Load strengths
                strength_col = f"reviewer_{j}_strengths"
                if strength_col in df_accepted.columns:
                    strength = df_accepted.iloc[i][strength_col]
                    if pd.notna(strength):
                        strengths.append(str(strength))
                    else:
                        strengths.append("")
                else:
                    strengths.append("")
            
            references[paper_name] = {
                'summaries': summaries,
                'weaknesses': weaknesses,
                'strengths': strengths
            }
    
    # Load rejected papers reference
    if REJECTED_REF_PATH.exists():
        df_rejected = pd.read_csv(REJECTED_REF_PATH)
        for i in range(len(df_rejected)):
            paper_name = f"rejected_paper_{i+1}"
            summaries = []
            weaknesses = []
            strengths = []
            for j in range(1, NUM_REVIEWERS + 1):
                # Load summaries
                summary_col = f"reviewer_{j}_summary"
                if summary_col in df_rejected.columns:
                    summary = df_rejected.iloc[i][summary_col]
                    if pd.notna(summary):
                        summaries.append(str(summary))
                    else:
                        summaries.append("")
                
                # Load weaknesses
                weakness_col = f"reviewer_{j}_weakness"
                if weakness_col in df_rejected.columns:
                    weakness = df_rejected.iloc[i][weakness_col]
                    if pd.notna(weakness):
                        weaknesses.append(str(weakness))
                    else:
                        weaknesses.append("")
                
                # Load strengths
                strength_col = f"reviewer_{j}_strengths"
                if strength_col in df_rejected.columns:
                    strength = df_rejected.iloc[i][strength_col]
                    if pd.notna(strength):
                        strengths.append(str(strength))
                    else:
                        strengths.append("")
                else:
                    strengths.append("")
            
            references[paper_name] = {
                'summaries': summaries,
                'weaknesses': weaknesses,
                'strengths': strengths
            }
    
    return references


def load_generated_report(paper_name: str) -> dict | None:
    """
    Load the generated final_report.json.
    
    Args:
        paper_name: e.g., 'accepted_paper_1'
    
    Returns:
        dict with report data or None if not found
    """
    report_path = RESULTS_DIR / paper_name / "final_report.json"
    
    if not report_path.exists():
        print(f"⚠️  No results found for {paper_name}")
        return None
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Clean markdown code blocks if present
        content = re.sub(r'^```json\s*', '', content.strip())
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        return json.loads(content)
    
    except json.JSONDecodeError as e:
        print(f"⚠️  Could not parse JSON for {paper_name}: {e}")
        return None
    except Exception as e:
        print(f"⚠️  Error loading {paper_name}: {e}")
        return None


def compute_cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def compute_per_weakness_metrics(
    generated_weaknesses: list[str],
    reference_weaknesses: list[str],
    model: "SentenceTransformer"
) -> tuple[list[WeaknessMatch], float, float, float]:
    """
    Compute per-weakness matching metrics.
    
    For each generated weakness:
    - Find the best matching reviewer and their weakness text
    - Compute the similarity score
    
    Also compute:
    - Average best match score across all generated weaknesses
    - Coverage score: % of reviewers that have at least one weakness matched above threshold
    - Aggregate similarity: compare all generated weaknesses (combined) vs all reference weaknesses (combined)
    
    Args:
        generated_weaknesses: List of generated weakness strings
        reference_weaknesses: List of reference weakness strings from reviewers
        model: SentenceTransformer for embeddings
    
    Returns:
        Tuple of (per_weakness_matches, avg_best_match, coverage_score, aggregate_similarity)
    """
    if not generated_weaknesses or not any(generated_weaknesses):
        return [], 0.0, 0.0, 0.0
    
    # Filter out empty reference weaknesses
    valid_refs = [(i, w) for i, w in enumerate(reference_weaknesses) if w and w.strip()]
    
    if not valid_refs:
        return [], 0.0, 0.0, 0.0
    
    # Encode all generated weaknesses
    gen_embeddings = [model.encode(w) for w in generated_weaknesses if w and w.strip()]
    valid_gen_weaknesses = [w for w in generated_weaknesses if w and w.strip()]
    
    if not gen_embeddings:
        return [], 0.0, 0.0, 0.0
    
    # Encode all reference weaknesses
    ref_embeddings = [model.encode(w) for i, w in valid_refs]
    
    # Per-weakness matching
    per_weakness_matches: list[WeaknessMatch] = []
    best_match_scores_per_reviewer = {i: 0.0 for i, _ in valid_refs}  # Track best match for each reviewer
    
    for gen_idx, (gen_weakness, gen_emb) in enumerate(zip(valid_gen_weaknesses, gen_embeddings)):
        best_score = 0.0
        best_reviewer_idx = 0
        best_ref_weakness = ""
        
        for ref_idx, (reviewer_idx, ref_weakness) in enumerate(valid_refs):
            sim = compute_cosine_similarity(gen_emb, ref_embeddings[ref_idx])
            if sim > best_score:
                best_score = sim
                best_reviewer_idx = reviewer_idx
                best_ref_weakness = ref_weakness
            
            # Update best match for this reviewer
            if sim > best_match_scores_per_reviewer[reviewer_idx]:
                best_match_scores_per_reviewer[reviewer_idx] = sim
        
        per_weakness_matches.append(WeaknessMatch(
            generated_weakness=gen_weakness,
            best_matching_reviewer=f"reviewer_{best_reviewer_idx + 1}",
            best_match_score=round(best_score, 4),
            matched_reference_weakness=best_ref_weakness
        ))
    
    # Average best match score
    avg_best_match = float(np.mean([m.best_match_score for m in per_weakness_matches]))
    
    # Coverage score: % of reviewers with at least one weakness matched above threshold
    covered_reviewers = sum(1 for score in best_match_scores_per_reviewer.values() if score >= COVERAGE_THRESHOLD)
    coverage_score = covered_reviewers / len(valid_refs) if valid_refs else 0.0
    
    # Aggregate similarity: combine all generated weaknesses vs combine all reference weaknesses
    combined_gen = " ".join(valid_gen_weaknesses)
    combined_ref = " ".join([w for _, w in valid_refs])
    
    combined_gen_emb = model.encode(combined_gen)
    combined_ref_emb = model.encode(combined_ref)
    aggregate_similarity = compute_cosine_similarity(combined_gen_emb, combined_ref_emb)
    
    return per_weakness_matches, round(avg_best_match, 4), round(coverage_score, 4), round(aggregate_similarity, 4)


def compute_per_strength_metrics(
    generated_strengths: list[str],
    reference_strengths: list[str],
    model: "SentenceTransformer"
) -> tuple[list[StrengthMatch], float, float, float]:
    """
    Compute per-strength matching metrics.
    
    For each generated strength:
    - Find the best matching reviewer and their strength text
    - Compute the similarity score
    
    Also compute:
    - Average best match score across all generated strengths
    - Coverage score: % of reviewers that have at least one strength matched above threshold
    - Aggregate similarity: compare all generated strengths (combined) vs all reference strengths (combined)
    
    Args:
        generated_strengths: List of generated strength strings
        reference_strengths: List of reference strength strings from reviewers
        model: SentenceTransformer for embeddings
    
    Returns:
        Tuple of (per_strength_matches, avg_best_match, coverage_score, aggregate_similarity)
    """
    if not generated_strengths or not any(generated_strengths):
        return [], 0.0, 0.0, 0.0
    
    # Filter out empty reference strengths
    valid_refs = [(i, s) for i, s in enumerate(reference_strengths) if s and s.strip()]
    
    if not valid_refs:
        return [], 0.0, 0.0, 0.0
    
    # Encode all generated strengths
    gen_embeddings = [model.encode(s) for s in generated_strengths if s and s.strip()]
    valid_gen_strengths = [s for s in generated_strengths if s and s.strip()]
    
    if not gen_embeddings:
        return [], 0.0, 0.0, 0.0
    
    # Encode all reference strengths
    ref_embeddings = [model.encode(s) for i, s in valid_refs]
    
    # Per-strength matching
    per_strength_matches: list[StrengthMatch] = []
    best_match_scores_per_reviewer = {i: 0.0 for i, _ in valid_refs}  # Track best match for each reviewer
    
    for gen_idx, (gen_strength, gen_emb) in enumerate(zip(valid_gen_strengths, gen_embeddings)):
        best_score = 0.0
        best_reviewer_idx = 0
        best_ref_strength = ""
        
        for ref_idx, (reviewer_idx, ref_strength) in enumerate(valid_refs):
            sim = compute_cosine_similarity(gen_emb, ref_embeddings[ref_idx])
            if sim > best_score:
                best_score = sim
                best_reviewer_idx = reviewer_idx
                best_ref_strength = ref_strength
            
            # Update best match for this reviewer
            if sim > best_match_scores_per_reviewer[reviewer_idx]:
                best_match_scores_per_reviewer[reviewer_idx] = sim
        
        per_strength_matches.append(StrengthMatch(
            generated_strength=gen_strength,
            best_matching_reviewer=f"reviewer_{best_reviewer_idx + 1}",
            best_match_score=round(best_score, 4),
            matched_reference_strength=best_ref_strength
        ))
    
    # Average best match score
    avg_best_match = float(np.mean([m.best_match_score for m in per_strength_matches]))
    
    # Coverage score: % of reviewers with at least one strength matched above threshold
    covered_reviewers = sum(1 for score in best_match_scores_per_reviewer.values() if score >= COVERAGE_THRESHOLD)
    coverage_score = covered_reviewers / len(valid_refs) if valid_refs else 0.0
    
    # Aggregate similarity: combine all generated strengths vs combine all reference strengths
    combined_gen = " ".join(valid_gen_strengths)
    combined_ref = " ".join([s for _, s in valid_refs])
    
    combined_gen_emb = model.encode(combined_gen)
    combined_ref_emb = model.encode(combined_ref)
    aggregate_similarity = compute_cosine_similarity(combined_gen_emb, combined_ref_emb)
    
    return per_strength_matches, round(avg_best_match, 4), round(coverage_score, 4), round(aggregate_similarity, 4)


def evaluate_paper(
    paper_name: str,
    generated_report: dict,
    reference_data: dict,
    model: "SentenceTransformer"
) -> PaperResult:
    """
    Evaluate a single paper by comparing generated content to reference data.
    
    Args:
        paper_name: e.g., 'accepted_paper_1'
        generated_report: The parsed final_report.json
        reference_data: Dict with 'summaries', 'weaknesses', and 'strengths' lists
        model: SentenceTransformer model for embeddings
    
    Returns:
        PaperResult with similarity scores
    """
    # Determine paper type
    paper_type = "accepted" if "accepted" in paper_name else "rejected"
    
    # Extract generated content
    generated_summary = generated_report.get("executive_summary", "")
    generated_weaknesses = generated_report.get("weaknesses", [])
    generated_strengths = generated_report.get("strengths", [])
    
    # Combine weaknesses/strengths into single strings for comparison
    generated_weakness_text = " ".join(generated_weaknesses) if generated_weaknesses else ""
    generated_strength_text = " ".join(generated_strengths) if generated_strengths else ""
    
    # Get reference data
    reference_summaries = reference_data.get('summaries', [])
    reference_weaknesses = reference_data.get('weaknesses', [])
    reference_strengths = reference_data.get('strengths', [])
    
    # Compute embeddings for generated content
    generated_summary_embedding = model.encode(generated_summary) if generated_summary else None
    generated_weakness_embedding = model.encode(generated_weakness_text) if generated_weakness_text else None
    generated_strength_embedding = model.encode(generated_strength_text) if generated_strength_text else None
    
    # Compute similarity with each reviewer
    reviewer_similarities = []
    summary_scores = []
    weakness_scores = []
    strength_scores = []
    
    for i in range(NUM_REVIEWERS):
        ref_summary = reference_summaries[i] if i < len(reference_summaries) else ""
        ref_weakness = reference_weaknesses[i] if i < len(reference_weaknesses) else ""
        ref_strength = reference_strengths[i] if i < len(reference_strengths) else ""
        
        # Summary similarity
        summary_sim = 0.0
        if generated_summary_embedding is not None and ref_summary:
            ref_summary_embedding = model.encode(ref_summary)
            summary_sim = compute_cosine_similarity(generated_summary_embedding, ref_summary_embedding)
        
        # Weakness similarity
        weakness_sim = 0.0
        if generated_weakness_embedding is not None and ref_weakness:
            ref_weakness_embedding = model.encode(ref_weakness)
            weakness_sim = compute_cosine_similarity(generated_weakness_embedding, ref_weakness_embedding)
        
        # Strength similarity
        strength_sim = 0.0
        if generated_strength_embedding is not None and ref_strength:
            ref_strength_embedding = model.encode(ref_strength)
            strength_sim = compute_cosine_similarity(generated_strength_embedding, ref_strength_embedding)
        
        reviewer_similarities.append(ReviewerSimilarity(
            reviewer_id=f"reviewer_{i+1}",
            reference_summary=ref_summary,
            summary_similarity=round(summary_sim, 4),
            reference_weakness=ref_weakness,
            weakness_similarity=round(weakness_sim, 4),
            reference_strength=ref_strength,
            strength_similarity=round(strength_sim, 4)
        ))
        
        if ref_summary:
            summary_scores.append(summary_sim)
        if ref_weakness:
            weakness_scores.append(weakness_sim)
        if ref_strength:
            strength_scores.append(strength_sim)
    
    # Compute aggregate summary metrics
    avg_summary_sim = float(np.mean(summary_scores)) if summary_scores else 0.0
    max_summary_sim = float(np.max(summary_scores)) if summary_scores else 0.0
    min_summary_sim = float(np.min(summary_scores)) if summary_scores else 0.0
    
    # Basic aggregate weakness metrics (still computed for backward compatibility)
    avg_weakness_sim = float(np.mean(weakness_scores)) if weakness_scores else 0.0
    max_weakness_sim = float(np.max(weakness_scores)) if weakness_scores else 0.0
    min_weakness_sim = float(np.min(weakness_scores)) if weakness_scores else 0.0
    
    # Basic aggregate strength metrics
    avg_strength_sim = float(np.mean(strength_scores)) if strength_scores else 0.0
    max_strength_sim = float(np.max(strength_scores)) if strength_scores else 0.0
    min_strength_sim = float(np.min(strength_scores)) if strength_scores else 0.0
    
    # Enhanced per-weakness metrics
    per_weakness_matches, avg_best_weakness_match, weakness_coverage, aggregate_weakness_sim = compute_per_weakness_metrics(
        generated_weaknesses, reference_weaknesses, model
    )
    
    # Enhanced per-strength metrics
    per_strength_matches, avg_best_strength_match, strength_coverage, aggregate_strength_sim = compute_per_strength_metrics(
        generated_strengths, reference_strengths, model
    )
    
    return PaperResult(
        paper_id=paper_name,
        paper_file=f"input/{paper_name}.txt",
        paper_type=paper_type,
        executive_summary=generated_summary,
        generated_weaknesses=generated_weaknesses,
        generated_strengths=generated_strengths,
        reviewer_similarities=reviewer_similarities,
        avg_summary_similarity=round(avg_summary_sim, 4),
        max_summary_similarity=round(max_summary_sim, 4),
        min_summary_similarity=round(min_summary_sim, 4),
        avg_weakness_similarity=round(avg_weakness_sim, 4),
        max_weakness_similarity=round(max_weakness_sim, 4),
        min_weakness_similarity=round(min_weakness_sim, 4),
        # Enhanced weakness metrics
        per_weakness_matches=per_weakness_matches,
        avg_best_weakness_match=avg_best_weakness_match,
        weakness_coverage_score=weakness_coverage,
        aggregate_weakness_similarity=aggregate_weakness_sim,
        # Strength metrics
        avg_strength_similarity=round(avg_strength_sim, 4),
        max_strength_similarity=round(max_strength_sim, 4),
        min_strength_similarity=round(min_strength_sim, 4),
        # Enhanced strength metrics
        per_strength_matches=per_strength_matches,
        avg_best_strength_match=avg_best_strength_match,
        strength_coverage_score=strength_coverage,
        aggregate_strength_similarity=aggregate_strength_sim
    )


def run_evaluation(model_name: str = "all-MiniLM-L6-v2") -> EvaluationSummary:
    """
    Run evaluation on all processed papers.
    
    Args:
        model_name: SentenceTransformer model to use for embeddings
    
    Returns:
        EvaluationSummary with all results
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        raise ImportError("sentence-transformers is required. Install with: pip install sentence-transformers")
    
    print(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    
    print("Loading reference data...")
    references = load_reference_data()
    print(f"  Found {len(references)} papers in reference data")
    
    # Find all processed papers
    if not RESULTS_DIR.exists():
        print(f"❌ Results directory not found: {RESULTS_DIR}")
        print("   Run `python eval/run_batch.py` first to process papers.")
        sys.exit(1)
    
    paper_dirs = [d for d in RESULTS_DIR.iterdir() if d.is_dir() and d.name.startswith(("accepted_", "rejected_"))]
    print(f"  Found {len(paper_dirs)} processed papers")
    
    if not paper_dirs:
        print("❌ No processed papers found. Run `python eval/run_batch.py` first.")
        sys.exit(1)
    
    # Evaluate each paper
    paper_results = []
    accepted_summary_scores = []
    rejected_summary_scores = []
    accepted_weakness_scores = []
    rejected_weakness_scores = []
    accepted_strength_scores = []
    rejected_strength_scores = []
    
    # Track enhanced weakness metrics
    all_best_weakness_match_scores = []
    all_weakness_coverage_scores = []
    all_aggregate_weakness_scores = []
    
    # Track enhanced strength metrics
    all_best_strength_match_scores = []
    all_strength_coverage_scores = []
    all_aggregate_strength_scores = []
    
    print("\nEvaluating papers...")
    print("-" * 120)
    
    for paper_dir in sorted(paper_dirs):
        paper_name = paper_dir.name
        
        # Load generated report
        generated_report = load_generated_report(paper_name)
        if generated_report is None:
            print(f"  ⏭️  Skipping {paper_name} (no valid output)")
            continue
        
        # Get reference data
        if paper_name not in references:
            print(f"  ⏭️  Skipping {paper_name} (no reference data)")
            continue
        
        reference_data = references[paper_name]
        
        # Evaluate
        result = evaluate_paper(paper_name, generated_report, reference_data, model)
        paper_results.append(result)
        
        # Track by type
        if result.paper_type == "accepted":
            accepted_summary_scores.append(result.avg_summary_similarity)
            accepted_weakness_scores.append(result.avg_weakness_similarity)
            accepted_strength_scores.append(result.avg_strength_similarity)
        else:
            rejected_summary_scores.append(result.avg_summary_similarity)
            rejected_weakness_scores.append(result.avg_weakness_similarity)
            rejected_strength_scores.append(result.avg_strength_similarity)
        
        # Track enhanced weakness metrics
        all_best_weakness_match_scores.append(result.avg_best_weakness_match)
        all_weakness_coverage_scores.append(result.weakness_coverage_score)
        all_aggregate_weakness_scores.append(result.aggregate_weakness_similarity)
        
        # Track enhanced strength metrics
        all_best_strength_match_scores.append(result.avg_best_strength_match)
        all_strength_coverage_scores.append(result.strength_coverage_score)
        all_aggregate_strength_scores.append(result.aggregate_strength_similarity)
        
        print(f"  ✅ {paper_name}: sum={result.avg_summary_similarity:.3f}, weak={result.avg_weakness_similarity:.3f}, str={result.avg_strength_similarity:.3f}")
    
    print("-" * 120)
    
    # Compute overall metrics
    all_summary_scores = [r.avg_summary_similarity for r in paper_results]
    all_weakness_scores = [r.avg_weakness_similarity for r in paper_results]
    all_strength_scores = [r.avg_strength_similarity for r in paper_results]
    
    summary = EvaluationSummary(
        timestamp=datetime.now(),
        total_papers=len(paper_results),
        # Summary metrics
        overall_avg_summary_similarity=round(float(np.mean(all_summary_scores)), 4) if all_summary_scores else 0.0,
        overall_std_summary_similarity=round(float(np.std(all_summary_scores)), 4) if all_summary_scores else 0.0,
        accepted_avg_summary_similarity=round(float(np.mean(accepted_summary_scores)), 4) if accepted_summary_scores else 0.0,
        rejected_avg_summary_similarity=round(float(np.mean(rejected_summary_scores)), 4) if rejected_summary_scores else 0.0,
        # Weakness metrics (original)
        overall_avg_weakness_similarity=round(float(np.mean(all_weakness_scores)), 4) if all_weakness_scores else 0.0,
        overall_std_weakness_similarity=round(float(np.std(all_weakness_scores)), 4) if all_weakness_scores else 0.0,
        accepted_avg_weakness_similarity=round(float(np.mean(accepted_weakness_scores)), 4) if accepted_weakness_scores else 0.0,
        rejected_avg_weakness_similarity=round(float(np.mean(rejected_weakness_scores)), 4) if rejected_weakness_scores else 0.0,
        # Enhanced weakness metrics
        overall_avg_best_weakness_match=round(float(np.mean(all_best_weakness_match_scores)), 4) if all_best_weakness_match_scores else 0.0,
        overall_avg_weakness_coverage=round(float(np.mean(all_weakness_coverage_scores)), 4) if all_weakness_coverage_scores else 0.0,
        overall_avg_aggregate_weakness_similarity=round(float(np.mean(all_aggregate_weakness_scores)), 4) if all_aggregate_weakness_scores else 0.0,
        # Strength metrics (original)
        overall_avg_strength_similarity=round(float(np.mean(all_strength_scores)), 4) if all_strength_scores else 0.0,
        overall_std_strength_similarity=round(float(np.std(all_strength_scores)), 4) if all_strength_scores else 0.0,
        accepted_avg_strength_similarity=round(float(np.mean(accepted_strength_scores)), 4) if accepted_strength_scores else 0.0,
        rejected_avg_strength_similarity=round(float(np.mean(rejected_strength_scores)), 4) if rejected_strength_scores else 0.0,
        # Enhanced strength metrics
        overall_avg_best_strength_match=round(float(np.mean(all_best_strength_match_scores)), 4) if all_best_strength_match_scores else 0.0,
        overall_avg_strength_coverage=round(float(np.mean(all_strength_coverage_scores)), 4) if all_strength_coverage_scores else 0.0,
        overall_avg_aggregate_strength_similarity=round(float(np.mean(all_aggregate_strength_scores)), 4) if all_aggregate_strength_scores else 0.0,
        paper_results=paper_results
    )
    
    return summary


def save_results(summary: EvaluationSummary):
    """Save evaluation results to files."""
    # Save full summary as JSON
    summary_path = RESULTS_DIR / "evaluation_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary.model_dump(mode='json'), f, indent=2, default=str)
    print(f"\n📄 Saved: {summary_path}")
    
    # Save per-paper results as CSV for easy viewing
    rows = []
    for result in summary.paper_results:
        row = {
            "paper_id": result.paper_id,
            "paper_type": result.paper_type,
            "avg_summary_similarity": result.avg_summary_similarity,
            "max_summary_similarity": result.max_summary_similarity,
            "min_summary_similarity": result.min_summary_similarity,
            # Weakness metrics
            "avg_weakness_similarity": result.avg_weakness_similarity,
            "max_weakness_similarity": result.max_weakness_similarity,
            "min_weakness_similarity": result.min_weakness_similarity,
            "avg_best_weakness_match": result.avg_best_weakness_match,
            "weakness_coverage_score": result.weakness_coverage_score,
            "aggregate_weakness_similarity": result.aggregate_weakness_similarity,
            "num_generated_weaknesses": len(result.generated_weaknesses),
            # Strength metrics
            "avg_strength_similarity": result.avg_strength_similarity,
            "max_strength_similarity": result.max_strength_similarity,
            "min_strength_similarity": result.min_strength_similarity,
            "avg_best_strength_match": result.avg_best_strength_match,
            "strength_coverage_score": result.strength_coverage_score,
            "aggregate_strength_similarity": result.aggregate_strength_similarity,
            "num_generated_strengths": len(result.generated_strengths),
        }
        # Add individual reviewer scores
        for rs in result.reviewer_similarities:
            row[f"{rs.reviewer_id}_summary_sim"] = rs.summary_similarity
            row[f"{rs.reviewer_id}_weakness_sim"] = rs.weakness_similarity
            row[f"{rs.reviewer_id}_strength_sim"] = rs.strength_similarity
        rows.append(row)
    
    df = pd.DataFrame(rows)
    csv_path = RESULTS_DIR / "per_paper_results.csv"
    df.to_csv(csv_path, index=False)
    print(f"📄 Saved: {csv_path}")
    
    # Save per-paper JSON to each paper's folder
    for result in summary.paper_results:
        paper_eval_path = RESULTS_DIR / result.paper_id / "evaluation.json"
        with open(paper_eval_path, 'w', encoding='utf-8') as f:
            json.dump(result.model_dump(mode='json'), f, indent=2)


def print_summary(summary: EvaluationSummary):
    """Print evaluation summary to console."""
    print("\n" + "="*120)
    print("EVALUATION RESULTS")
    print("="*120)
    
    print(f"\nTotal Papers Evaluated: {summary.total_papers}")
    
    print(f"\n--- Summary Similarity (executive_summary vs reviewer summaries) ---")
    print(f"  Overall Average:  {summary.overall_avg_summary_similarity:.4f}")
    print(f"  Standard Dev:     {summary.overall_std_summary_similarity:.4f}")
    print(f"  Accepted Papers:  {summary.accepted_avg_summary_similarity:.4f}")
    print(f"  Rejected Papers:  {summary.rejected_avg_summary_similarity:.4f}")
    
    print(f"\n--- Weakness Similarity ---")
    print(f"  Basic (combined):     Avg={summary.overall_avg_weakness_similarity:.4f}, Std={summary.overall_std_weakness_similarity:.4f}")
    print(f"  Accepted / Rejected:  {summary.accepted_avg_weakness_similarity:.4f} / {summary.rejected_avg_weakness_similarity:.4f}")
    print(f"  Best Match Score:     {summary.overall_avg_best_weakness_match:.4f}")
    print(f"  Coverage Score:       {summary.overall_avg_weakness_coverage:.4f}")
    print(f"  Aggregate Similarity: {summary.overall_avg_aggregate_weakness_similarity:.4f}")
    
    print(f"\n--- Strength Similarity ---")
    print(f"  Basic (combined):     Avg={summary.overall_avg_strength_similarity:.4f}, Std={summary.overall_std_strength_similarity:.4f}")
    print(f"  Accepted / Rejected:  {summary.accepted_avg_strength_similarity:.4f} / {summary.rejected_avg_strength_similarity:.4f}")
    print(f"  Best Match Score:     {summary.overall_avg_best_strength_match:.4f}")
    print(f"  Coverage Score:       {summary.overall_avg_strength_coverage:.4f}")
    print(f"  Aggregate Similarity: {summary.overall_avg_aggregate_strength_similarity:.4f}")
    
    print("\nPer-Paper Results:")
    print("-" * 130)
    print(f"{'Paper':<25} {'Type':<10} {'Summary':<10} {'Weak Avg':<10} {'Weak Best':<10} {'Str Avg':<10} {'Str Best':<10}")
    print("-" * 130)
    
    for result in sorted(summary.paper_results, key=lambda x: x.paper_id):
        print(f"{result.paper_id:<25} {result.paper_type:<10} {result.avg_summary_similarity:<10.4f} {result.avg_weakness_similarity:<10.4f} {result.avg_best_weakness_match:<10.4f} {result.avg_strength_similarity:<10.4f} {result.avg_best_strength_match:<10.4f}")
    
    print("-" * 130)
    print(f"\nResults saved to: {RESULTS_DIR}/")
    print("\nMetric Explanations:")
    print("  - Summary:    Cosine similarity of executive_summary vs each reviewer summary")
    print("  - Weak/Str Avg:  Average cosine similarity of all items combined vs each reviewer")
    print("  - Best Match: For each generated item, find best-matching reviewer → average those scores")
    print("  - Coverage:   Fraction of reviewers that have at least one item matched above threshold (0.5)")
    print("  - Aggregate:  Compare all generated items combined vs all reference items combined")


def main():
    """Main entry point."""
    print("="*80)
    print("PAPER REVIEW EVALUATION")
    print("="*80)
    print(f"Comparing: CrewAI outputs vs. reference reviewer data")
    print(f"Metrics: Cosine similarity of sentence embeddings")
    print(f"  1. executive_summary vs reviewer summaries")
    print(f"  2. weaknesses vs reviewer weaknesses")
    print()
    
    # Run evaluation
    summary = run_evaluation()
    
    # Save results
    save_results(summary)
    
    # Print summary
    print_summary(summary)


if __name__ == "__main__":
    main()
