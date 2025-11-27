from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from tools.custom_tool import MarkdownToPdfTool


@CrewBase
class PaperReviewCrew():
    """Paper Review crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # REMOVED: scraper_agent (uses pdf_path)

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

    @task
    def pdf_generation(self) -> Task:
        return Task(
            config=self.tasks_config['pdf_generation'],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Paper Review crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )