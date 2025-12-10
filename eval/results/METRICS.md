# Evaluation Metrics

This document explains the metrics used to evaluate the automated paper review system against reference reviewer data from the DeepReview-13K dataset.

## Overview

We compare three types of generated content against reference reviewer comments:
1. **Executive Summary** vs. Reviewer Summaries
2. **Weaknesses** vs. Reviewer Weaknesses
3. **Strengths** vs. Reviewer Strengths

All similarity scores use **cosine similarity** of sentence embeddings from the `all-MiniLM-L6-v2` model.

---

## Summary Metrics

| Metric | Description |
|--------|-------------|
| `avg_summary_similarity` | Average cosine similarity between the generated executive summary and each of the 4 reviewer summaries |
| `max_summary_similarity` | Highest similarity score among the 4 reviewers |
| `min_summary_similarity` | Lowest similarity score among the 4 reviewers |

---

## Weakness Metrics

### Basic Metrics
| Metric | Description |
|--------|-------------|
| `avg_weakness_similarity` | Average similarity of all generated weaknesses (combined) vs. each reviewer's weaknesses |
| `max_weakness_similarity` | Highest similarity score among the 4 reviewers |
| `min_weakness_similarity` | Lowest similarity score among the 4 reviewers |

### Enhanced Metrics
| Metric | Description |
|--------|-------------|
| `avg_best_weakness_match` | For each generated weakness, find the best-matching reviewer → average those best-match scores |
| `weakness_coverage_score` | Fraction of reviewers (0-1) that have at least one weakness matched above threshold (0.5) |
| `aggregate_weakness_similarity` | Similarity of all generated weaknesses combined vs. all reference weaknesses combined |

### Per-Weakness Matching
Each generated weakness is matched to its best-matching reviewer, stored in `per_weakness_matches`:
- `generated_weakness`: The weakness text from our system
- `best_matching_reviewer`: Which reviewer (1-4) had the most similar weakness
- `best_match_score`: The cosine similarity score
- `matched_reference_weakness`: The actual reviewer weakness text that matched

---

## Strength Metrics

### Basic Metrics
| Metric | Description |
|--------|-------------|
| `avg_strength_similarity` | Average similarity of all generated strengths (combined) vs. each reviewer's strengths |
| `max_strength_similarity` | Highest similarity score among the 4 reviewers |
| `min_strength_similarity` | Lowest similarity score among the 4 reviewers |

### Enhanced Metrics
| Metric | Description |
|--------|-------------|
| `avg_best_strength_match` | For each generated strength, find the best-matching reviewer → average those best-match scores |
| `strength_coverage_score` | Fraction of reviewers (0-1) that have at least one strength matched above threshold (0.5) |
| `aggregate_strength_similarity` | Similarity of all generated strengths combined vs. all reference strengths combined |

### Per-Strength Matching
Each generated strength is matched to its best-matching reviewer, stored in `per_strength_matches`:
- `generated_strength`: The strength text from our system
- `best_matching_reviewer`: Which reviewer (1-4) had the most similar strength
- `best_match_score`: The cosine similarity score
- `matched_reference_strength`: The actual reviewer strength text that matched

---

## Aggregate Metrics (Across All Papers)

The `evaluation_summary.json` contains overall metrics computed across all evaluated papers:

| Metric | Description |
|--------|-------------|
| `overall_avg_*` | Mean across all papers |
| `overall_std_*` | Standard deviation across all papers |
| `accepted_avg_*` | Mean for accepted papers only |
| `rejected_avg_*` | Mean for rejected papers only |

---

## Interpreting the Scores

| Score Range | Interpretation |
|-------------|----------------|
| 0.8 - 1.0 | Very high similarity (near identical content) |
| 0.6 - 0.8 | Good similarity (captures main points) |
| 0.4 - 0.6 | Moderate similarity (some overlap) |
| 0.2 - 0.4 | Low similarity (different focus) |
| 0.0 - 0.2 | Very low similarity (unrelated content) |

### Why Weakness/Strength Scores May Be Lower Than Summary Scores

- **Subjectivity**: Different reviewers focus on different aspects
- **Granularity**: Our system may identify different specific issues
- **Complementarity**: Lower similarity doesn't mean incorrect—it may mean our system found additional valid points

---

## Output Files

| File | Description |
|------|-------------|
| `evaluation_summary.json` | Complete evaluation results with all metrics |
| `per_paper_results.csv` | Tabular view of key metrics per paper |
| `<paper_name>/evaluation.json` | Detailed per-paper results including per-weakness/strength matching |

---

## Technical Details

- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Similarity Metric**: Cosine similarity
- **Coverage Threshold**: 0.5 (for determining if a reviewer's points are "covered")
- **Reference Data**: 4 reviewers per paper from DeepReview-13K dataset
