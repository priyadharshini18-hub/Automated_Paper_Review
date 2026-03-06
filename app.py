"""
Gradio UI for Automated Paper Review System.
Run from project root: python app.py
"""

import gradio as gr
import sys
import os
import json
import re
import tempfile
from pathlib import Path

# ── Setup paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)                          # ensure relative paths work
sys.path.insert(0, str(PROJECT_ROOT / "src"))   # so `from crew import ...` works

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from main import run_review as _run_review


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_available_papers() -> list[str]:
    input_folder = PROJECT_ROOT / "input"
    return [f"input/{p.name}" for p in sorted(input_folder.glob("*.txt"))]


def extract_pdf_text(pdf_path: str) -> str:
    import pymupdf
    doc = pymupdf.open(pdf_path)
    text = "".join(page.get_text() for page in doc)
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    tmp.write(text)
    tmp.close()
    return tmp.name


def read_output_files() -> tuple[str, str, dict]:
    output_dir = PROJECT_ROOT / "output"
    summary, critique, final_report = "", "", {}

    p = output_dir / "paper_summary.md"
    if p.exists():
        summary = p.read_text(encoding="utf-8")

    p = output_dir / "critique_decision.md"
    if p.exists():
        critique = p.read_text(encoding="utf-8")

    p = output_dir / "final_report.json"
    if p.exists():
        try:
            content = p.read_text(encoding="utf-8").strip()
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if m:
                content = m.group()
            final_report = json.loads(content)
        except Exception:
            pass

    return summary, critique, final_report


def format_report_as_markdown(report: dict) -> str:
    if not report:
        return "_No report was generated._"
    lines = []
    lines.append(f"# {report.get('title', 'Untitled Paper')}\n")
    if report.get("authors"):
        lines.append(f"**Authors:** {report['authors']}  ")
    if report.get("date_reviewed"):
        lines.append(f"**Date Reviewed:** {report['date_reviewed']}")
    lines.append("\n---\n")
    for key, heading in [
        ("executive_summary", "Executive Summary"),
        ("problem_statement", "Problem Statement"),
        ("methodology", "Methodology"),
        ("key_results", "Key Results"),
        ("conclusions", "Conclusions"),
    ]:
        if report.get(key):
            lines.append(f"## {heading}\n\n{report[key]}\n")
    for key, heading in [
        ("research_objectives", "Research Objectives"),
        ("strengths", "Strengths"),
        ("weaknesses", "Weaknesses"),
        ("future_work", "Future Work"),
    ]:
        if report.get(key):
            lines.append(f"## {heading}\n")
            for item in report[key]:
                lines.append(f"- {item}")
            lines.append("")
    if report.get("metrics"):
        lines.append("## Metrics\n")
        lines.append("| Metric | Value | Explanation |")
        lines.append("|--------|-------|-------------|")
        for m in report["metrics"]:
            lines.append(f"| {m.get('name','')} | {m.get('value','')} | {m.get('explanation','')} |")
        lines.append("")
    return "\n".join(lines)


# ── HTML report generator ─────────────────────────────────────────────────────

def generate_html_report(report: dict, summary: str, critique: str) -> str:
    """Write a self-contained styled HTML report; return its file path."""
    title   = report.get("title", "Untitled Paper")
    authors = report.get("authors") or "N/A"
    date    = report.get("date_reviewed") or ""

    verdict = "APPROVED" if "APPROVED" in critique.upper() else "REJECTED"
    verdict_color = "#059669" if verdict == "APPROVED" else "#dc2626"

    def li_items(lst):
        return "".join(f"<li>{i}</li>" for i in lst) if lst else ""

    def metric_rows(lst):
        if not lst:
            return ""
        return "".join(
            f"<tr><td>{m.get('name','')}</td>"
            f"<td><strong>{m.get('value','')}</strong></td>"
            f"<td>{m.get('explanation','')}</td></tr>"
            for m in lst
        )

    def card(accent, heading, body_html):
        return f"""
        <div class="card" style="border-left-color:{accent}">
            <h2>{heading}</h2>
            {body_html}
        </div>"""

    sections = ""

    if report.get("executive_summary"):
        sections += card("#2563eb", "Executive Summary",
                         f"<p>{report['executive_summary']}</p>")
    if report.get("problem_statement"):
        sections += card("#7c3aed", "Problem Statement",
                         f"<p>{report['problem_statement']}</p>")
    if report.get("research_objectives"):
        sections += card("#2563eb", "Research Objectives",
                         f"<ul>{li_items(report['research_objectives'])}</ul>")
    if report.get("methodology"):
        sections += card("#d97706", "Methodology",
                         f"<p>{report['methodology']}</p>")
    if report.get("key_results"):
        sections += card("#2563eb", "Key Results",
                         f"<p>{report['key_results']}</p>")
    if report.get("metrics"):
        sections += card("#7c3aed", "Metrics", f"""
            <table>
              <tr><th>Metric</th><th>Value</th><th>Explanation</th></tr>
              {metric_rows(report['metrics'])}
            </table>""")
    if report.get("strengths"):
        sections += card("#059669", "Strengths",
                         f"<ul>{li_items(report['strengths'])}</ul>")
    if report.get("weaknesses"):
        sections += card("#dc2626", "Weaknesses",
                         f"<ul>{li_items(report['weaknesses'])}</ul>")
    if report.get("conclusions"):
        sections += card("#2563eb", "Conclusions",
                         f"<p>{report['conclusions']}</p>")
    if report.get("future_work"):
        sections += card("#d97706", "Future Work",
                         f"<ul>{li_items(report['future_work'])}</ul>")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Paper Review — {title}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f1f5f9;color:#1e293b;line-height:1.7}}
  .page{{max-width:900px;margin:2rem auto;padding:0 1.5rem 4rem}}
  .header{{
    background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%);
    color:white;border-radius:16px;padding:2.5rem 2.5rem 2rem;margin-bottom:1.5rem
  }}
  .header .label{{font-size:.8rem;opacity:.7;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.5rem}}
  .header h1{{font-size:1.65rem;font-weight:800;margin-bottom:.5rem;line-height:1.3}}
  .header .meta{{font-size:.875rem;opacity:.75;margin-top:.4rem}}
  .verdict{{
    display:inline-block;padding:.35rem 1.2rem;border-radius:999px;
    font-weight:700;font-size:.82rem;letter-spacing:.06em;
    color:white;background:{verdict_color};margin-top:1rem
  }}
  .card{{
    background:white;border-radius:12px;padding:1.75rem 2rem;
    margin-bottom:1.25rem;box-shadow:0 1px 4px rgba(0,0,0,.07);
    border-left:4px solid #2563eb
  }}
  h2{{
    font-size:.8rem;font-weight:700;text-transform:uppercase;
    letter-spacing:.07em;color:#64748b;margin-bottom:.85rem
  }}
  p{{margin-bottom:.5rem}}
  ul{{padding-left:1.4rem;margin-top:.4rem}}
  ul li{{margin-bottom:.4rem}}
  table{{width:100%;border-collapse:collapse;margin-top:.5rem;font-size:.9rem}}
  th{{background:#f1f5f9;text-align:left;padding:.6rem .8rem;font-weight:600;color:#475569}}
  td{{padding:.6rem .8rem;border-bottom:1px solid #e2e8f0;vertical-align:top}}
  tr:last-child td{{border-bottom:none}}
  .footer{{text-align:center;font-size:.8rem;color:#94a3b8;margin-top:2rem}}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="label">AI-Generated Paper Review</div>
    <h1>{title}</h1>
    <div class="meta">Authors: {authors} &nbsp;·&nbsp; {date}</div>
    <div class="verdict">{verdict}</div>
  </div>

  {sections}

  <div class="footer">
    Generated by Automated Paper Review System &nbsp;·&nbsp; CrewAI + GPT-4o-mini
  </div>
</div>
</body>
</html>"""

    out_path = PROJECT_ROOT / "output" / "paper_review_report.html"
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


# ── Core review function ──────────────────────────────────────────────────────

ERR = ("_No critique._", "_No report._", "{}", gr.update(visible=False))


def run_paper_review(input_mode: str, paper_choice: str, uploaded_file, pasted_text: str):
    tmp_file = None
    try:
        if input_mode == "Paste text":
            text = (pasted_text or "").strip()
            if not text:
                return ("**Please paste some paper text before running.**", *ERR)
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
            tmp.write(text)
            tmp.close()
            tmp_file = paper_path = tmp.name

        elif input_mode == "Upload PDF":
            if uploaded_file is None:
                return ("**Please upload a PDF file before running.**", *ERR)
            uploaded_path = Path(uploaded_file)
            if uploaded_path.suffix.lower() == ".pdf":
                try:
                    tmp_file = paper_path = extract_pdf_text(str(uploaded_path))
                except Exception as e:
                    return (f"**Error extracting PDF:** {e}", *ERR)
            else:
                paper_path = str(uploaded_path)

        else:
            if not paper_choice:
                return ("**Please select a paper from the dropdown.**", *ERR)
            paper_path = str(PROJECT_ROOT / paper_choice)

        result = _run_review(paper_path)
        if result is None:
            return ("**Review failed.** Check file and API key.", *ERR)

        summary, critique, final_report = read_output_files()
        report_md  = format_report_as_markdown(final_report)
        raw_json   = json.dumps(final_report, indent=2, ensure_ascii=False)
        html_path  = generate_html_report(final_report, summary, critique)

        return (summary, critique, report_md, raw_json,
                gr.update(value=html_path, visible=True))

    except Exception:
        import traceback
        return (f"**Error:**\n```\n{traceback.format_exc()}\n```", *ERR)
    finally:
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)


# ── Custom CSS ────────────────────────────────────────────────────────────────
CSS = """
/* ---------- Labels (Summary, Final Report etc.) ---------- */

label {
    color: #1e293b !important;
    font-weight: 600;
}


/* ---------- Tabs ---------- */

.tab-nav {
    border-bottom: 2px solid #e2e8f0;
}

/* default tab */
.gradio-container .tab-nav button {
    color: #64748b !important;
    font-weight: 600;
    border-bottom: 2px solid transparent;
    background: transparent !important;
}

/* hover tab */
.gradio-container .tab-nav button:hover {
    background: transparent !important;
    color: #2563eb !important;
}

/* active tab */
.gradio-container .tab-nav button[aria-selected="true"] {
    background: transparent !important;
    color: #2563eb !important;
    border-bottom: 2px solid #2563eb !important;
}


/* ---------- Buttons ---------- */

button {
    font-weight: 600 !important;
}


/* ---------- Textboxes ---------- */

textarea, input {
    color: #1e293b !important;
}
"""

# ── UI layout ─────────────────────────────────────────────────────────────────

PLACEHOLDER = "_Run a review to see results here._"
MODES = ["Select existing paper", "Upload PDF", "Paste text"]

with gr.Blocks(title="Automated Paper Review", css=CSS) as demo:

    gr.HTML("""
        <div id="header">
            <h1>Automated Paper Review</h1>
            <p>Multi-agent AI pipeline &nbsp;·&nbsp; CrewAI + GPT-4o-mini
               &nbsp;·&nbsp; Summarise &middot; Critique &middot; Report</p>
        </div>
    """)

    with gr.Row(equal_height=False):

        # Left panel
        with gr.Column(scale=1, min_width=300, elem_id="input-panel"):
            gr.Markdown("### Paper Input")

            input_mode = gr.Radio(choices=MODES, value=MODES[0],
                                  label="Input method", interactive=True)

            with gr.Column(visible=True) as col_select:
                paper_dropdown = gr.Dropdown(
                    choices=get_available_papers(), label="Choose a paper",
                    value=None, interactive=True)

            with gr.Column(visible=False) as col_upload:
                file_upload = gr.File(label="Upload PDF", file_types=[".pdf"])

            with gr.Column(visible=False) as col_paste:
                pasted_text = gr.Textbox(
                    label="Paste paper text",
                    placeholder="Paste the full paper text here…",
                    lines=12, max_lines=30)

            run_btn = gr.Button("Run Review", variant="primary",
                                size="lg", elem_id="run-btn")

            download_btn = gr.DownloadButton(
                label="Download Report (HTML)",
                value=None, visible=False,
                size="lg", elem_id="download-btn")

            gr.HTML("""
                <div id="pipeline-info">
                    <strong>Pipeline (sequential)</strong><br>
                    1. Summarizer Agent &rarr; structured summary<br>
                    2. Critique Agent &rarr; APPROVED / REJECTED<br>
                    3. Synthesizer Agent &rarr; JSON report<br><br>
                    <em>Typically takes 2–5 minutes.</em>
                </div>
            """)

        # Right panel
        with gr.Column(scale=2, elem_id="results-panel"):
            with gr.Tabs():
                with gr.Tab("Summary"):
                    summary_out = gr.Markdown(value=PLACEHOLDER)
                with gr.Tab("Critique"):
                    critique_out = gr.Markdown(value=PLACEHOLDER)
                with gr.Tab("Final Report"):
                    report_out = gr.Markdown(value=PLACEHOLDER)
                with gr.Tab("Raw JSON"):
                    json_out = gr.Code(language="json", value="{}")

    def switch_mode(mode):
        return (
            gr.update(visible=(mode == "Select existing paper")),
            gr.update(visible=(mode == "Upload PDF")),
            gr.update(visible=(mode == "Paste text")),
        )

    input_mode.change(fn=switch_mode, inputs=input_mode,
                      outputs=[col_select, col_upload, col_paste])

    run_btn.click(
        fn=run_paper_review,
        inputs=[input_mode, paper_dropdown, file_upload, pasted_text],
        outputs=[summary_out, critique_out, report_out, json_out, download_btn],
    )
    

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
