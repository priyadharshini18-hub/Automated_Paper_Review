from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import pymupdf


class MyCustomToolInput(BaseModel):
    """Input schema for MyCustomTool."""
    argument: str = Field(..., description="Description of the argument.")

class MyCustomTool(BaseTool):
    name: str = "Name of my tool"
    description: str = (
        "Clear description for what this tool is useful for, your agent will need this information to use it."
    )
    args_schema: Type[BaseModel] = MyCustomToolInput

    def _run(self, argument: str) -> str:
        # Implementation goes here
        return "this is an example of a tool output, ignore it and move along."
    
    

class PdfToTextInput(BaseModel):
    """Input schema for PdfToTextTool."""
    pdf_path: str = Field(..., description="Path to the input PDF file.")
    output_path: str = Field(
        default="document_text.txt",
        description="Path to write extracted text (UTF-8).",
    )


class PdfToTextTool(BaseTool):
    name: str = "PDF to Text Extractor"
    description: str = (
        "Extract text from a PDF using pymupdf and write it to a UTF-8 text file."
    )
    args_schema: Type[BaseModel] = PdfToTextInput

    def _run(self, pdf_path: str, output_path: str = "document_text.txt") -> str:
        doc = pymupdf.open(pdf_path)
        doc_text = ""
        for page in doc:
            text = page.get_text()
            doc_text += text
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(doc_text)
        return f"Successfully extracted text from {pdf_path} and saved to {output_path}.\n\nExtracted text:\n\n{doc_text}"

