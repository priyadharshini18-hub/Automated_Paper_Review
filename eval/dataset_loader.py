"""Dataset loader for DeepReview-13K dataset."""

from pathlib import Path

import pandas as pd
from datasets import load_dataset

# Constants
NUM_PAPERS = 5
NUM_REVIEWERS = 4
OUTPUT_DIR = Path(__file__).parent


def load_and_preprocess_data(num_rows: int = 100) -> pd.DataFrame:
    """Load dataset and preprocess columns."""
    dataset = load_dataset("WestlakeNLP/DeepReview-13K")
    df = pd.DataFrame(dataset['test'][:num_rows])
    
    # Clean string columns
    for column in ['inputs', 'outputs', 'reviewer_comments']:
        df[column] = df[column].str.strip('[]')
    
    # Parse rating column and filter for valid entries
    df['rating'] = df['rating'].apply(lambda x: eval(x) if isinstance(x, str) else x)
    df = df[df['rating'].apply(lambda x: isinstance(x, list) and len(x) == NUM_REVIEWERS)]
    
    return df.reset_index(drop=True)


def parse_columns(df: pd.DataFrame) -> tuple[list, list, list]:
    """Parse string columns into dictionaries."""
    inputs = [eval(row) for row in df['inputs']]
    outputs = [eval(row) for row in df['outputs']]
    reviewer_comments = [eval(row) for row in df['reviewer_comments']]
    return inputs, outputs, reviewer_comments


def get_shortest_paper_indices(inputs: list, n: int = NUM_PAPERS) -> list[int]:
    """Get indices of the n shortest papers by content length."""
    lengths = {i: len(inp[1]['content']) for i, inp in enumerate(inputs)}
    return sorted(lengths, key=lengths.get)[:n]


def build_reference_row(
    paper_id: str,
    reviewer_comments: list,
    weakness_key: str = 'weakness'
) -> dict:
    """Build a reference row from reviewer comments."""
    row = {'id': paper_id}
    for j in range(NUM_REVIEWERS):
        content = reviewer_comments[j]['content']
        row[f'reviewer_{j+1}_comments'] = content
        row[f'reviewer_{j+1}_summary'] = content['summary']
        row[f'reviewer_{j+1}_weakness'] = content[weakness_key]
    return row


def process_papers(
    df: pd.DataFrame,
    inputs: list,
    reviewer_comments: list,
    shortest_indices: list,
    decision_type: str,
    weakness_key: str = 'weakness'
) -> pd.DataFrame:
    """Process papers and export to files."""
    df_shortest = df.iloc[shortest_indices].reset_index(drop=True)
    rows = []
    
    for i, orig_idx in enumerate(shortest_indices):
        # Export paper content
        paper_content = inputs[orig_idx][1]['content']
        output_path = OUTPUT_DIR.parent / 'input' / f'{decision_type}_paper_{i+1}.txt'
        output_path.write_text(paper_content)
        
        # Build reference row
        row = build_reference_row(
            paper_id=df_shortest.at[i, 'id'],
            reviewer_comments=reviewer_comments[orig_idx],
            weakness_key=weakness_key
        )
        rows.append(row)
    
    return pd.DataFrame(rows)


def main():
    """Main processing pipeline."""
    # Load and preprocess data
    df = load_and_preprocess_data()
    
    # Split by decision
    df_accepted = df[df['decision'] == 'Accept'].reset_index(drop=True)
    df_rejected = df[df['decision'] == 'Reject'].reset_index(drop=True)
    
    # Parse columns for each split
    inputs_accepted, _, comments_accepted = parse_columns(df_accepted)
    inputs_rejected, _, comments_rejected = parse_columns(df_rejected)
    
    # Get shortest paper indices
    shortest_accepted = get_shortest_paper_indices(inputs_accepted)
    shortest_rejected = get_shortest_paper_indices(inputs_rejected)
    
    # Process and export accepted papers
    df_accepted_ref = process_papers(
        df_accepted, inputs_accepted, comments_accepted,
        shortest_accepted, 'accepted', weakness_key='weakness'
    )
    
    # Process and export rejected papers
    df_rejected_ref = process_papers(
        df_rejected, inputs_rejected, comments_rejected,
        shortest_rejected, 'rejected', weakness_key='weaknesses'
    )
    
    # Save reference CSVs
    df_accepted_ref.to_csv(OUTPUT_DIR / 'accepted_reference.csv', index=False)
    df_rejected_ref.to_csv(OUTPUT_DIR / 'rejected_reference.csv', index=False)
    
    print(f"Exported {len(df_accepted_ref)} accepted and {len(df_rejected_ref)} rejected papers.")


if __name__ == '__main__':
    main()