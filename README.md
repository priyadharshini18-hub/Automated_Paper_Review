# Automated Paper Review Crew

Welcome to the Automated Paper Review Crew project, powered by [crewAI](https://crewai.com). This template is designed to help you set up a multi-agent AI system with ease, leveraging the powerful and flexible framework provided by crewAI. Our goal is to enable your agents to collaborate effectively on extracting and analyzing research papers, maximizing their collective intelligence and capabilities.

## Features

- **PDF Text Extraction**: Automatically extract clean text from research papers
- **Intelligent Summarization**: Generate structured summaries with key sections:
  - Problem Statement
  - Objectives
  - Methodology
  - Results
  - Conclusions
<Other features in progress>

## Installation

Ensure you have Python >=3.10 <3.14 (Python 3.11 recommended) installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv:
```bash
pip install uv
```

Next, navigate to your project directory and install the dependencies:
```bash
uv pip install crewai crewai-tools pyyaml python-dotenv pymupdf
```

(Optional) Lock the dependencies and install them by using the CLI command:
```bash
crewai install
```

### Customizing

**Add your API keys into the `.env` file**

Create a `.env` file in the root directory:
```
GROQ_API_KEY=your_groq_api_key_here
MODEL=gemini/gemini-2.0-flash-lite-001
```

- Modify `src/config/agents.yaml` to define your agents
- Modify `src/config/tasks.yaml` to define your tasks
- Modify `src/crew.py` to add your own logic, tools and specific args
- Modify `src/main.py` to add custom inputs for your agents and tasks

## Running the Project

1. **Add your research paper**: Place your PDF file in the `input/` folder (e.g., `input/paper1.pdf`)

2. **Run the crew**: To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:
```bash
crewai run
```

This command initializes the Automated Paper Review Crew, assembling the agents and assigning them tasks as defined in your configuration.

## Output

The crew generates two files:
- `output/paper_text.txt`: Extracted text from the PDF
- `output/paper_summary.md`: Structured summary with Problem Statement, Objectives, Methodology, Results, and Conclusions

## Understanding Your Crew

The Automated Paper Review Crew is composed of multiple AI agents, each with unique roles, goals, and tools:

1. **Scraper Agent**: Extracts clean text from PDF research papers using the custom PDF to Text Extractor tool
2. **Summarizer Agent**: Analyzes the extracted text and produces comprehensive, structured summaries

These agents collaborate on a series of tasks, defined in `config/tasks.yaml`, leveraging their collective skills to achieve complex objectives. The `config/agents.yaml` file outlines the capabilities and configurations of each agent in your crew.

## Project Structure
```
Automated_Paper_Review/
├── src/
│   ├── config/
│   │   ├── agents.yaml      # Agent definitions
│   │   └── tasks.yaml       # Task definitions
│   ├── tools/
│   │   └── custom_tool.py   # PDF extraction tool
│   ├── crew.py              # Crew orchestration
│   └── main.py              # Entry point
├── input/                   # Place PDFs here
├── output/                  # Generated outputs
├── .env                     # API keys (not in git)
└── pyproject.toml          # Project dependencies
```