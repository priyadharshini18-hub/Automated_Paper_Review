from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from src.tools.custom_tool import PdfToTextTool, MarkdownToPdfTool


@CrewBase
class PaperReviewCrew():
    """Paper Review crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'


    @agent
    def scrapper_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['scrapper_agent'],
            tools=[PdfToTextTool()],  # Add tool instance here
            verbose=True
        )

    @agent
    def summarizer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['summarizer_agent'],
            verbose=True
        )

    @agent
    def critique_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['critique_agent'],
            verbose=True
        )

    @agent
    def synthesizer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['synthesizer_agent'],
            verbose=True
        )

    @agent
    def pdf_generator_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['pdf_generator_agent'],
            tools=[MarkdownToPdfTool()],
            verbose=True
        )

    @task
    def text_extractor(self) -> Task:
        return Task(
            config=self.tasks_config['text_extractor'],
        )

    @task
    def paper_summarizer(self) -> Task:
        return Task(
            config=self.tasks_config['paper_summarizer'],
        )

    @task
    def summary_critique(self) -> Task:
        return Task(
            config=self.tasks_config['summary_critique'],
        )

    @task
    def final_report_generation(self) -> Task:
        return Task(
            config=self.tasks_config['final_report_generation'],
        )

    @task
    def pdf_generation(self) -> Task:
        return Task(
            config=self.tasks_config['pdf_generation'],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Deep Researcher crew"""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
