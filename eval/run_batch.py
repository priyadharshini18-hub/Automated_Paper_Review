"""Batch processing script to run CrewAI on all papers."""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
import os
import json
import re

# Load environment variables
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

from crew import PaperReviewCrew


def get_paper_name(paper_file: str) -> str:
    """Extract paper name from file path (e.g., 'accepted_paper_1')."""
    return Path(paper_file).stem


def ensure_output_dir(paper_name: str) -> Path:
    """Create and return per-paper output directory."""
    output_dir = project_root / "eval" / "results" / paper_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def clean_json_output(raw_output: str) -> dict:
    """Clean and parse JSON from LLM output (handles markdown code blocks)."""
    # Remove markdown code blocks if present
    cleaned = raw_output.strip()
    
    # Remove ```json or ``` markers
    cleaned = re.sub(r'^```json\s*', '', cleaned)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    
    # Try to find JSON object
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        cleaned = match.group()
    
    return json.loads(cleaned)


def run_single_paper(paper_file: str) -> dict:
    """
    Run the paper review crew on a single paper.
    
    Returns:
        dict with paper_name, output_dir, and success status
    """
    paper_path = project_root / paper_file
    
    if not paper_path.exists():
        print(f"❌ File not found: {paper_file}")
        return {"success": False, "error": "File not found"}
    
    paper_name = get_paper_name(paper_file)
    output_dir = ensure_output_dir(paper_name)
    
    # Read paper content
    with open(paper_path, 'r', encoding='utf-8') as f:
        paper_content = f.read()
    
    print(f"\n{'='*60}")
    print(f"Processing: {paper_name}")
    print(f"  Length: {len(paper_content):,} chars (~{len(paper_content)//4:,} tokens)")
    print(f"  Output: {output_dir}")
    print('='*60)
    
    try:
        # Run crew
        crew = PaperReviewCrew()
        result = crew.crew().kickoff(inputs={
            'paper_file': str(paper_path),
            'paper_content': paper_content,
        })
        
        # Save raw result
        raw_output_path = output_dir / "raw_output.txt"
        with open(raw_output_path, 'w', encoding='utf-8') as f:
            f.write(result.raw)
        
        # Try to parse and save final report as clean JSON
        try:
            final_report = clean_json_output(result.raw)
            with open(output_dir / "final_report.json", 'w', encoding='utf-8') as f:
                json.dump(final_report, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved final_report.json")
        except json.JSONDecodeError as e:
            print(f"⚠️  Could not parse JSON: {e}")
            # Save as-is
            with open(output_dir / "final_report.txt", 'w', encoding='utf-8') as f:
                f.write(result.raw)
        
        # Save individual task outputs if available
        for i, task_output in enumerate(result.tasks_output):
            task_name = f"task_{i+1}"
            if hasattr(task_output, 'description') and task_output.description:
                # Extract task name from description
                if 'summary' in task_output.description.lower():
                    task_name = "paper_summary"
                elif 'critique' in task_output.description.lower():
                    task_name = "critique_decision"
                elif 'report' in task_output.description.lower():
                    task_name = "final_report"
            
            with open(output_dir / f"{task_name}.txt", 'w', encoding='utf-8') as f:
                f.write(str(task_output.raw) if hasattr(task_output, 'raw') else str(task_output))
        
        print(f"✅ Completed: {paper_name}")
        return {
            "success": True,
            "paper_name": paper_name,
            "output_dir": str(output_dir)
        }
        
    except Exception as e:
        print(f"❌ Error processing {paper_name}: {e}")
        
        # Save error log
        with open(output_dir / "error.txt", 'w', encoding='utf-8') as f:
            f.write(str(e))
        
        return {
            "success": False,
            "paper_name": paper_name,
            "error": str(e)
        }


def run_all_papers():
    """Run crew on all papers in the input folder."""
    input_dir = project_root / "input"
    
    # Get all paper files
    paper_files = sorted(input_dir.glob("*.txt"))
    
    if not paper_files:
        print("❌ No paper files found in input/")
        return
    
    print(f"Found {len(paper_files)} papers to process")
    print(f"GEMINI_API_KEY: {'✅ Set' if os.getenv('GEMINI_API_KEY') else '❌ Not set'}")
    
    results = []
    for paper_file in paper_files:
        relative_path = f"input/{paper_file.name}"
        result = run_single_paper(relative_path)
        results.append(result)
    
    # Summary
    print("\n" + "="*60)
    print("BATCH PROCESSING COMPLETE")
    print("="*60)
    
    successful = sum(1 for r in results if r.get("success"))
    print(f"✅ Successful: {successful}/{len(results)}")
    
    if successful < len(results):
        print("\nFailed papers:")
        for r in results:
            if not r.get("success"):
                print(f"  - {r.get('paper_name', 'unknown')}: {r.get('error', 'unknown error')}")
    
    # Save batch results
    results_path = project_root / "eval" / "results" / "batch_results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {results_path}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Run single paper
        paper_file = sys.argv[1]
        run_single_paper(paper_file)
    else:
        # Run all papers
        run_all_papers()


if __name__ == "__main__":
    main()
