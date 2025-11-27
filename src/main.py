import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from crew import PaperReviewCrew

def run_review(paper_file: str):
    """
    Run the paper review crew on a specific text file.
    
    Args:
        paper_file: Path to the text file (e.g., 'input/accepted_paper_1.txt')
    """
    # Verify file exists (handle both absolute and relative paths)
    paper_path = Path(paper_file)
    
    # If relative path, check from project root
    if not paper_path.is_absolute():
        project_root = Path(__file__).resolve().parent.parent
        paper_path = project_root / paper_file
    
    if not paper_path.exists():
        print(f"Error: File not found: {paper_file}")
        print("\nAvailable files in input/:")
        input_folder = Path(__file__).resolve().parent.parent / "input"
        for f in input_folder.glob("*.txt"):
            print(f"  - input/{f.name}")
        return
    
    # Read the paper content
    with open(paper_path, 'r', encoding='utf-8') as f:
        paper_content = f.read()
    
    print(f"Loaded: {paper_file}")
    print(f"   Length: {len(paper_content):,} characters (~{len(paper_content)//4:,} tokens)")
    print(f"   Using GEMINI_API_KEY: {'Set' if os.getenv('GEMINI_API_KEY') else 'Not set'}")
    print("\n" + "="*50)
    print("Starting Paper Review...")
    print("="*50 + "\n")
    
    # Run your crew with BOTH path and content
    crew = PaperReviewCrew()
    result = crew.crew().kickoff(inputs={
        'paper_file': str(paper_path),
        'paper_content': paper_content,  # <-- ADD THIS
    })
    
    print("\n" + "="*50)
    print("Review Complete!")
    print("="*50)
    print(result.raw)
    return result


def list_papers():
    """List all available papers in the input folder."""
    input_folder = Path(__file__).resolve().parent.parent / "input"
    print("\nAvailable papers:")
    print("-" * 40)
    for i, f in enumerate(sorted(input_folder.glob("*.txt")), 1):
        print(f"  {i}. input/{f.name}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <paper_file>")
        print("\nExamples:")
        print("  python main.py input/accepted_paper_1.txt")
        print("  python main.py input/rejected_paper_3.txt")
        list_papers()
        sys.exit(1)
    
    paper_file = sys.argv[1]
    run_review(paper_file)