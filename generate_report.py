#!/usr/bin/env python3
"""
Standalone script to generate report from existing graded CSV files.
"""
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from evalsys.reporting import emit_report

def main():
    # Paths
    scores_dir = Path("data/out/graded")
    dataset_path = Path("data/out/dataset.jsonl")
    empty_answers_dir = scores_dir
    output_html = scores_dir / "report.html"  # Put report in the graded folder
    
    print(f"Generating report from {scores_dir}")
    print(f"Found CSV files:")
    for csv_file in scores_dir.glob("scores__*.csv"):
        print(f"  - {csv_file.name}")
    for csv_file in scores_dir.glob("empty_answers__*.csv"):
        print(f"  - {csv_file.name} (empty answers)")
    
    print(f"Dataset: {dataset_path}")
    print(f"Output: {output_html}")
    
    # Generate the reports
    html_path, public_html_path, summary_path = emit_report(scores_dir, output_html, dataset_path, empty_answers_dir)
    print(f"\nReports generated:")
    print(f"  HTML (full): {html_path}")
    print(f"  HTML (public): {public_html_path}")
    print(f"  Markdown: {summary_path}")

if __name__ == "__main__":
    main()
