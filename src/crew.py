from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
# Removed: MarkdownToPdfTool import (not needed for eval)


@CrewBase
class PaperReviewCrew():
    """Paper Review crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

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

    # Removed: pdf_generator_agent (not needed for eval)

    @task
    def text_reader(self) -> Task:
        return Task(
            config=self.tasks_config['text_reader'],
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

    # Removed: pdf_generation task (not needed for eval)

    @crew
    def crew(self) -> Crew:
        """Creates the Paper Review crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )