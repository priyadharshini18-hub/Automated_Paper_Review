import sys
from pathlib import Path
from dotenv import load_dotenv
import os
import json
import re

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from crew import PaperReviewCrew

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_paper_name(paper_file: str) -> str:
    """Extract paper name from file path (e.g., 'accepted_paper_1')."""
    return Path(paper_file).stem


def get_output_dir(paper_name: str, use_eval_results: bool = False) -> Path:
    """
    Get output directory for a paper.
    
    Args:
        paper_name: e.g., 'accepted_paper_1'
        use_eval_results: If True, save to eval/results/{paper_name}/
                         If False, save to output/
    """
    if use_eval_results:
        output_dir = PROJECT_ROOT / "eval" / "results" / paper_name
    else:
        output_dir = PROJECT_ROOT / "output"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def clean_json_output(raw_output: str) -> dict:
    """Clean and parse JSON from LLM output (handles markdown code blocks)."""
    cleaned = raw_output.strip()
    
    # Remove markdown code blocks if present
    cleaned = re.sub(r'^```json\s*', '', cleaned)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    
    # Try to find JSON object
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        cleaned = match.group()
    
    return json.loads(cleaned)


def save_results(result, paper_name: str, output_dir: Path):
    """Save crew results to output directory."""
    # Save raw output
    raw_path = output_dir / "raw_output.txt"
    with open(raw_path, 'w', encoding='utf-8') as f:
        f.write(result.raw)
    
    # Try to parse and save as clean JSON
    try:
        final_report = clean_json_output(result.raw)
        json_path = output_dir / "final_report.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        print(f"📄 Saved: {json_path}")
    except json.JSONDecodeError as e:
        print(f"⚠️  Could not parse JSON: {e}")
        txt_path = output_dir / "final_report.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(result.raw)
        print(f"📄 Saved (as text): {txt_path}")


def run_review(paper_file: str, use_eval_results: bool = False):
    """
    Run the paper review crew on a specific text file.
    
    Args:
        paper_file: Path to the text file (e.g., 'input/accepted_paper_1.txt')
        use_eval_results: If True, save to eval/results/{paper_name}/
    """
    # Verify file exists (handle both absolute and relative paths)
    paper_path = Path(paper_file)
    
    # If relative path, check from project root
    if not paper_path.is_absolute():
        paper_path = PROJECT_ROOT / paper_file
    
    if not paper_path.exists():
        print(f"Error: File not found: {paper_file}")
        print("\nAvailable files in input/:")
        input_folder = PROJECT_ROOT / "input"
        for f in input_folder.glob("*.txt"):
            print(f"  - input/{f.name}")
        return None
    
    # Get paper name and output directory
    paper_name = get_paper_name(paper_file)
    output_dir = get_output_dir(paper_name, use_eval_results)
    
    # Read the paper content
    with open(paper_path, 'r', encoding='utf-8') as f:
        paper_content = f.read()
    
    print(f"Loaded: {paper_file}")
    print(f"   Length: {len(paper_content):,} characters (~{len(paper_content)//4:,} tokens)")
    print(f"   Output: {output_dir}")
    print(f"   GEMINI_API_KEY: {'✅ Set' if os.getenv('GEMINI_API_KEY') else '❌ Not set'}")
    print("\n" + "="*50)
    print("Starting Paper Review...")
    print("="*50 + "\n")
    
    # Run crew
    crew = PaperReviewCrew()
    result = crew.crew().kickoff(inputs={
        'paper_file': str(paper_path),
        'paper_content': paper_content,
    })
    
    # Save results
    save_results(result, paper_name, output_dir)
    
    print("\n" + "="*50)
    print("✅ Review Complete!")
    print("="*50)
    
    return result


def list_papers():
    """List all available papers in the input folder."""
    input_folder = PROJECT_ROOT / "input"
    print("\nAvailable papers:")
    print("-" * 40)
    for i, f in enumerate(sorted(input_folder.glob("*.txt")), 1):
        print(f"  {i}. input/{f.name}")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run paper review crew")
    parser.add_argument("paper_file", nargs="?", help="Path to paper file (e.g., input/accepted_paper_1.txt)")
    parser.add_argument("--eval", action="store_true", help="Save results to eval/results/ for evaluation")
    parser.add_argument("--list", action="store_true", help="List available papers")
    
    args = parser.parse_args()
    
    if args.list or not args.paper_file:
        print("Usage: python main.py <paper_file> [--eval]")
        print("\nOptions:")
        print("  --eval    Save results to eval/results/{paper_name}/ for evaluation")
        print("  --list    List available papers")
        print("\nExamples:")
        print("  python main.py input/accepted_paper_1.txt")
        print("  python main.py input/accepted_paper_1.txt --eval")
        list_papers()
        sys.exit(0 if args.list else 1)
    
    run_review(args.paper_file, use_eval_results=args.eval)