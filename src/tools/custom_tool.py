from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import pymupdf
import markdown
import os
import re

# Try to import weasyprint, fall back to xhtml2pdf, then reportlab
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False

try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except (ImportError, OSError):
    XHTML2PDF_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


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


class MarkdownToPdfInput(BaseModel):
    """Input schema for MarkdownToPdfTool."""
    markdown_path: str = Field(..., description="Path to the input Markdown file (.md)")
    output_pdf_path: str = Field(
        ...,
        description="Path to the output PDF file (e.g., 'output/paper_name_report.pdf')"
    )


class MarkdownToPdfTool(BaseTool):
    name: str = "Markdown to PDF Converter"
    description: str = (
        "Convert a Markdown file to a professionally formatted PDF document. "
        "Supports tables, headers, lists, and other markdown formatting. "
        "Ideal for converting research paper review reports to PDF format."
    )
    args_schema: Type[BaseModel] = MarkdownToPdfInput

    def _run(self, markdown_path: str, output_pdf_path: str) -> str:
        try:
            # Read the markdown file
            if not os.path.exists(markdown_path):
                return f"Error: Markdown file not found at {markdown_path}"

            with open(markdown_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            # Convert markdown to HTML with extensions for tables and other features
            html_content = markdown.markdown(
                markdown_content,
                extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
            )

            # Add CSS styling for professional PDF appearance
            css_style = """
            <style>
                @page {
                    size: A4;
                    margin: 2.5cm;
                }
                body {
                    font-family: Arial, Helvetica, sans-serif;
                    font-size: 11pt;
                    line-height: 1.6;
                    color: #333;
                }
                h1 {
                    font-size: 24pt;
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                    margin-top: 20px;
                }
                h2 {
                    font-size: 18pt;
                    color: #34495e;
                    margin-top: 20px;
                    border-bottom: 1px solid #bdc3c7;
                    padding-bottom: 5px;
                }
                h3 {
                    font-size: 14pt;
                    color: #2c3e50;
                    margin-top: 15px;
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 15px 0;
                }
                th, td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }
                th {
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                }
                tr:nth-child(even) {
                    background-color: #f2f2f2;
                }
                code {
                    background-color: #f4f4f4;
                    padding: 2px 5px;
                    font-family: Courier, monospace;
                }
                pre {
                    background-color: #f4f4f4;
                    padding: 10px;
                    overflow-x: auto;
                }
                ul, ol {
                    margin: 10px 0;
                    padding-left: 30px;
                }
                li {
                    margin: 5px 0;
                }
                blockquote {
                    border-left: 4px solid #3498db;
                    padding-left: 15px;
                    margin: 15px 0;
                    color: #555;
                    font-style: italic;
                }
                hr {
                    border: none;
                    border-top: 1px solid #bdc3c7;
                    margin: 20px 0;
                }
            </style>
            """

            # Create complete HTML document
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                {css_style}
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # Ensure output directory exists
            output_dir = os.path.dirname(output_pdf_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Convert HTML to PDF using available library
            if WEASYPRINT_AVAILABLE:
                try:
                    HTML(string=full_html).write_pdf(output_pdf_path)
                    return f"Successfully converted {markdown_path} to PDF: {output_pdf_path} (using WeasyPrint)"
                except Exception as e:
                    # If weasyprint fails, try fallbacks
                    if XHTML2PDF_AVAILABLE:
                        return self._convert_with_xhtml2pdf(full_html, output_pdf_path, markdown_path)
                    elif REPORTLAB_AVAILABLE:
                        return self._convert_with_reportlab(markdown_content, output_pdf_path, markdown_path)
                    else:
                        raise e
            elif XHTML2PDF_AVAILABLE:
                return self._convert_with_xhtml2pdf(full_html, output_pdf_path, markdown_path)
            elif REPORTLAB_AVAILABLE:
                return self._convert_with_reportlab(markdown_content, output_pdf_path, markdown_path)
            else:
                return "Error: No PDF library available. Please install 'reportlab' (pip install reportlab)"

        except Exception as e:
            return f"Error converting markdown to PDF: {str(e)}"

    def _convert_with_xhtml2pdf(self, html_content: str, output_pdf_path: str, markdown_path: str) -> str:
        """Helper method to convert HTML to PDF using xhtml2pdf"""
        try:
            with open(output_pdf_path, "wb") as pdf_file:
                pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

            if pisa_status.err:
                return f"Error: xhtml2pdf reported errors during conversion"

            return f"Successfully converted {markdown_path} to PDF: {output_pdf_path} (using xhtml2pdf)"
        except Exception as e:
            return f"Error with xhtml2pdf conversion: {str(e)}"

    def _convert_with_reportlab(self, markdown_content: str, output_pdf_path: str, markdown_path: str) -> str:
        """Helper method to convert markdown to PDF using reportlab (simpler, no HTML needed)"""
        try:
            # Create PDF document
            doc = SimpleDocTemplate(output_pdf_path, pagesize=A4,
                                   leftMargin=2.5*cm, rightMargin=2.5*cm,
                                   topMargin=2.5*cm, bottomMargin=2.5*cm)

            # Container for PDF elements
            story = []

            # Define styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontSize=11, leading=16))

            # Custom styles
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                        fontSize=24, textColor=colors.HexColor('#2c3e50'),
                                        spaceAfter=12, spaceBefore=12)
            h2_style = ParagraphStyle('CustomH2', parent=styles['Heading2'],
                                     fontSize=18, textColor=colors.HexColor('#34495e'),
                                     spaceAfter=10, spaceBefore=10)
            h3_style = ParagraphStyle('CustomH3', parent=styles['Heading3'],
                                     fontSize=14, textColor=colors.HexColor('#2c3e50'),
                                     spaceAfter=8, spaceBefore=8)
            normal_style = styles['Justify']

            # Split markdown into lines and process
            lines = markdown_content.split('\n')
            i = 0
            in_table = False
            table_data = []

            while i < len(lines):
                line = lines[i].strip()

                # Handle headers
                if line.startswith('# '):
                    story.append(Paragraph(line[2:], title_style))
                    story.append(Spacer(1, 0.2*cm))
                elif line.startswith('## '):
                    story.append(Paragraph(line[3:], h2_style))
                    story.append(Spacer(1, 0.15*cm))
                elif line.startswith('### '):
                    story.append(Paragraph(line[4:], h3_style))
                    story.append(Spacer(1, 0.1*cm))
                # Handle horizontal rules
                elif line.startswith('---') or line.startswith('***'):
                    story.append(Spacer(1, 0.3*cm))
                # Handle tables
                elif '|' in line and not in_table:
                    in_table = True
                    table_data = []
                    # Process table header
                    cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                    table_data.append(cells)
                elif '|' in line and in_table:
                    # Skip separator line
                    if re.match(r'^\|[\s\-:]+\|', line):
                        i += 1
                        continue
                    cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                    table_data.append(cells)
                elif in_table and not '|' in line:
                    # End of table
                    in_table = False
                    if table_data:
                        t = Table(table_data)
                        t.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 11),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')])
                        ]))
                        story.append(t)
                        story.append(Spacer(1, 0.3*cm))
                        table_data = []
                # Handle bullet points
                elif line.startswith('- ') or line.startswith('* '):
                    text = '• ' + line[2:]
                    story.append(Paragraph(text, normal_style))
                # Handle numbered lists
                elif re.match(r'^\d+\.\s', line):
                    story.append(Paragraph(line, normal_style))
                # Handle normal paragraphs
                elif line:
                    # Escape XML special characters
                    text = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(text, normal_style))
                    story.append(Spacer(1, 0.2*cm))
                else:
                    # Empty line
                    story.append(Spacer(1, 0.1*cm))

                i += 1

            # Build PDF
            doc.build(story)

            return f"Successfully converted {markdown_path} to PDF: {output_pdf_path} (using ReportLab)"

        except Exception as e:
            return f"Error with ReportLab conversion: {str(e)}"

