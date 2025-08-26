# Complete Unstructured MCP Integration Guide

This guide shows how to integrate the Unstructured MCP server into your Deep Agents research project to add document processing capabilities.

## Overview

The Unstructured MCP server allows your research agent to:
- Process PDFs, Word docs, presentations, images, and 40+ file types
- Extract structured text with formatting, tables, and metadata
- Combine document analysis with web research
- Handle local files seamlessly within your research workflow

## Prerequisites

1. **Unstructured Account & API Key**
   - Sign up at [unstructured.io](https://unstructured.io/?modal=try-for-free)
   - Get your API key from [platform.unstructured.io](https://platform.unstructured.io)

2. **Python Dependencies**
   - `uv` package manager (install with `pip install uv`)
   - Your existing Deep Agents project setup

## Step 1: Create MCP Server Directory

From your project root:

```bash
# Create and initialize MCP server directory
mkdir mcp-unstructured-server
cd mcp-unstructured-server

# Initialize with uv and install dependencies
uv init .
uv add "mcp[cli]" "unstructured-client>=0.30.6" python-dotenv

# Create virtual environment
uv venv
# Activate it (macOS/Linux: source .venv/bin/activate, Windows: .venv\Scripts\activate)
```

## Step 2: Create MCP Server Code

Create `mcp-unstructured-server/doc_processor.py`:

```python
import os
from dotenv import load_dotenv
import json
from unstructured_client import UnstructuredClient
from typing import AsyncIterator
from dataclasses import dataclass
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP, Context
from unstructured_client.models import operations, shared

@dataclass
class AppContext:
    client: UnstructuredClient

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manages the Unstructured API client lifecycle."""
    api_key = os.getenv("UNSTRUCTURED_API_KEY")
    if not api_key:
        raise ValueError("UNSTRUCTURED_API_KEY environment variable is required")

    client = UnstructuredClient(api_key_auth=api_key)
    try:
        yield AppContext(client=client)
    finally:
        # No cleanup needed for the API client.
        pass

# Create the MCP server instance.
mcp = FastMCP("unstructured-partition-mcp", lifespan=app_lifespan, dependencies=["unstructured-client", "python-dotenv"])

# Specify the absolute path to the local directory to store processed files.
PROCESSED_FILES_FOLDER = os.getenv("UNSTRUCTURED_OUTPUT_DIR", "/tmp/unstructured_output")

def load_environment_variables() -> None:
    """
    Load environment variables from .env file.
    Raises an error if critical environment variables are missing.
    """
    load_dotenv()
    required_vars = [
        "UNSTRUCTURED_API_KEY"
    ]

    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Missing required environment variable: {var}")

def json_to_text(file_path) -> str:
    with open(file_path, 'r') as file:
        elements = json.load(file)

    doc_texts = []

    for element in elements:
        text = element.get("text", "").strip()
        element_type = element.get("type", "")
        metadata = element.get("metadata", {})

        if element_type == "Title":
            doc_texts.append(f"<h1> {text}</h1><br>")
        elif element_type == "Header":
            doc_texts.append(f"<h2> {text}</h2><br/>")
        elif element_type == "NarrativeText" or element_type == "UncategorizedText":
            doc_texts.append(f"<p>{text}</p>")
        elif element_type == "ListItem":
            doc_texts.append(f"<li>{text}</li>")
        elif element_type == "PageNumber":
            doc_texts.append(f"Page number: {text}")
        elif element_type == "Table":
            table_html = metadata.get("text_as_html", "")
            doc_texts.append(table_html)  # Keep the table as HTML.
        else:
            doc_texts.append(text)

    return " ".join(doc_texts)

@mcp.tool()
async def process_document(ctx: Context, filepath: str) -> str:
    """
    Sends the document to Unstructured for processing. 
    Returns the processed contents of the document
    
    Args:
        filepath: The local path to the document.
    """

    filepath = os.path.abspath(filepath)

    if not os.path.isfile(filepath):
        return "File does not exist"

    # Check whether Unstructured supports the file's extension.
    _, ext = os.path.splitext(filepath)
    supported_extensions = {".abw", ".bmp", ".csv", ".cwk", ".dbf", ".dif", ".doc", ".docm", ".docx", ".dot",
                            ".dotm", ".eml", ".epub", ".et", ".eth", ".fods", ".gif", ".heic", ".htm", ".html",
                            ".hwp", ".jpeg", ".jpg", ".md", ".mcw", ".mw", ".odt", ".org", ".p7s", ".pages",
                            ".pbd", ".pdf", ".png", ".pot", ".potm", ".ppt", ".pptm", ".pptx", ".prn", ".rst",
                            ".rtf", ".sdp", ".sgl", ".svg", ".sxg", ".tiff", ".txt", ".tsv", ".uof", ".uos1",
                            ".uos2", ".web", ".webp", ".wk2", ".xls", ".xlsb", ".xlsm", ".xlsx", ".xlw", ".xml",
                            ".zabw"}

    if ext.lower() not in supported_extensions:
        return "File extension not supported by Unstructured"

    client = ctx.request_context.lifespan_context.client
    file_basename = os.path.basename(filepath)

    # Ensure output directory exists
    os.makedirs(PROCESSED_FILES_FOLDER, exist_ok=True)

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=shared.Files(
                content=open(filepath, "rb"),
                file_name=filepath,
            ),
            strategy=shared.Strategy.AUTO,
        ),
    )

    try:
        res = client.general.partition(request=req)
        element_dicts = [element for element in res.elements]
        json_elements = json.dumps(element_dicts, indent=2)
        output_json_file_path = os.path.join(PROCESSED_FILES_FOLDER, f"{file_basename}.json")
        with open(output_json_file_path, "w") as file:
            file.write(json_elements)

        return json_to_text(output_json_file_path)
    except Exception as e:
        return f"The following exception happened during file processing: {e}"

if __name__ == "__main__":
    load_environment_variables()
    # Initialize and run the server.
    mcp.run(transport='stdio')
```

## Step 3: Create MCP Server Environment File

Create `mcp-unstructured-server/.env`:

```bash
UNSTRUCTURED_API_KEY="your-unstructured-api-key-here"
```

## Step 4: Update Your Main Project's MCP Tools

Add this function to your `deepagents/mcp_tools.py`:

```python
def get_unstructured_mcp_tools() -> List[object]:
    """Connect to Unstructured MCP server for document processing."""
    api_key = os.getenv("UNSTRUCTURED_API_KEY", "")
    if not api_key:
        print("[unstructured_mcp] UNSTRUCTURED_API_KEY not found, skipping")
        return []
    
    # Get the absolute path to the MCP server directory
    mcp_server_dir = os.getenv("UNSTRUCTURED_MCP_DIR", "")
    if not mcp_server_dir:
        print("[unstructured_mcp] UNSTRUCTURED_MCP_DIR not found, skipping")
        return []
    
    server_config = {
        "unstructured_partition": {
            "transport": "stdio",
            "command": "uv",
            "args": [
                "--directory", 
                mcp_server_dir,
                "run",
                "doc_processor.py"
            ],
            "env": {
                "UNSTRUCTURED_API_KEY": api_key,
                "PATH": os.environ.get("PATH", "")
            }
        }
    }
    
    print(f"[unstructured_mcp] Starting Unstructured MCP server...")
    
    try:
        return _get_mcp_tools_sync(server_config)
    except Exception as e:
        print(f"[unstructured_mcp] Failed to start: {type(e).__name__}: {e}")
        return []


# Update the get_all_mcp_tools function to include Unstructured
def get_all_mcp_tools() -> List[object]:
    """Get all available MCP tools."""
    all_tools = []
    
    # Existing servers
    all_tools.extend(get_firecrawl_mcp_tools())
    all_tools.extend(get_microsoft_learn_mcp_tools())
    
    # Add Unstructured server
    all_tools.extend(get_unstructured_mcp_tools())
    
    return all_tools
```

## Step 5: Update Your Main Project Environment

Add these variables to your main project's `.env` file:

```bash
# Unstructured MCP Configuration
UNSTRUCTURED_API_KEY=your-unstructured-api-key-here
UNSTRUCTURED_MCP_DIR=/absolute/path/to/your/mcp-unstructured-server
UNSTRUCTURED_OUTPUT_DIR=/tmp/unstructured_output

# Existing configurations...
TAVILY_API_KEY=your-tavily-api-key
FIRECRAWL_API_KEY=your-firecrawl-api-key
# etc...
```

**Important**: Replace the paths with your actual absolute paths:
- `UNSTRUCTURED_MCP_DIR` should point to your `mcp-unstructured-server` directory
- `UNSTRUCTURED_OUTPUT_DIR` is where processed files will be stored

## Step 6: Update Your Research Agent

Modify your `research_agent.py` to include enhanced instructions for document processing:

```python
import os
from typing import Literal

from tavily import TavilyClient
from dotenv import load_dotenv

from deepagents import create_deep_agent, SubAgent
from deepagents.mcp_tools import get_all_mcp_tools
 
# Load environment variables from the project root .env file
load_dotenv(dotenv_path="../../.env")
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Search tool to use to do research
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    search_docs = tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
    return search_docs

# Updated research instructions to include document processing
research_instructions = """You are an expert researcher with advanced document processing capabilities. Your job is to conduct thorough research and write polished reports.

The first thing you should do is to write the original user question to `question.txt` so you have a record of it.

## Available Tools:

### Core Research Tools:
1. **internet_search** - Web search for current information and trends
2. **process_document** - Process local documents (PDF, DOCX, PPT, images, etc.) using Unstructured AI to extract structured text, tables, and metadata
3. **research-agent** - Delegate specific research topics to specialized sub-agents
4. **critique-agent** - Get detailed feedback and suggestions for improving your reports

### Document Processing Workflow:
When users provide documents or ask you to analyze files:

1. **Extract Document Content**: Use `process_document(filepath="/path/to/document")` to extract structured content
2. **Analyze Structure**: The tool extracts titles, headers, paragraphs, tables, lists, and metadata
3. **Integrate with Research**: Combine document insights with web research for comprehensive analysis
4. **Reference Sources**: Include both document findings and web sources in your citations

### Supported File Types:
- **Documents**: PDF, DOCX, DOC, ODT, RTF, TXT, MD
- **Presentations**: PPTX, PPT, ODP
- **Spreadsheets**: XLSX, XLS, CSV
- **Images**: PNG, JPG, JPEG, TIFF, BMP, SVG
- **Web**: HTML, HTM, XML
- **Email**: EML
- **And 30+ more formats**

### Research Strategy:
1. **Document-First Approach**: If documents are provided, process them first to understand the context
2. **Web Research Enhancement**: Use internet search to find current information that complements document content
3. **Comparative Analysis**: Compare document findings with current market data, trends, and expert opinions
4. **Comprehensive Integration**: Weave document insights seamlessly with web research in your final report

Use the research-agent to conduct deep research on specific topics. It will respond with detailed answers.

When you have enough information, write your final report to `final_report.md`

You can call the critique-agent for feedback, then iterate on your report until satisfied.

Only edit files one at a time to avoid conflicts.

<report_instructions>

CRITICAL: Make sure the answer is written in the same language as the human messages! 

Please create a detailed answer to the overall research brief that:
1. Is well-organized with proper headings (# for title, ## for sections, ### for subsections)
2. Includes specific facts and insights from both documents AND web research
3. References sources using [Title](URL) format for web sources and [Document: filename] for processed documents
4. Provides balanced, thorough analysis combining document evidence with current information
5. Includes a "Sources" section at the end with all referenced links and documents

Document Integration Guidelines:
- When referencing document content, cite as: [Document: filename, page/section if available]
- Highlight key findings from documents separately from web research when relevant
- Use document data as primary evidence, web research for context and current trends
- If document data conflicts with web sources, note the discrepancy and publication dates

Structure examples:
- **Analysis Reports**: Overview → Document Findings → Current Market Research → Synthesis → Conclusions
- **Comparison Studies**: Introduction → Document A Analysis → Document B Analysis → Current Context → Comparison → Recommendations
- **Trend Analysis**: Historical Data (from docs) → Current Trends (web research) → Future Projections → Implications

For each section:
- Use clear, professional language without self-reference
- Provide comprehensive analysis with document evidence
- Include relevant tables, figures, or data points from processed documents
- Cross-reference document findings with current information

<Citation Rules>
- Number sources sequentially (1,2,3,4...) without gaps
- Web sources: [1] Source Title: URL
- Documents: [2] Document: filename.pdf (processed via Unstructured AI)
- End with ### Sources section listing all numbered references
- Citations are crucial for credibility and follow-up research
</Citation Rules>
</report_instructions>

You have access to internet search, document processing, file operations, and specialized research agents.
"""

# Your existing sub-agent definitions remain the same
sub_research_prompt = """You are a dedicated researcher. Your job is to conduct research based on the users questions.

Conduct thorough research and then reply to the user with a detailed answer to their question

only your FINAL answer will be passed on to the user. They will have NO knowledge of anything except your final message, so your final report should be your final message!"""

research_sub_agent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions. Only give this researcher one topic at a time. Do not pass multiple sub questions to this researcher. Instead, you should break down a large topic into the necessary components, and then call multiple research agents in parallel, one for each sub question.",
    "prompt": sub_research_prompt,
    "tools": ["internet_search"],
}

sub_critique_prompt = """You are a dedicated editor. You are being tasked to critique a report.

You can find the report at `final_report.md`.

You can find the question/topic for this report at `question.txt`.

The user may ask for specific areas to critique the report in. Respond to the user with a detailed critique of the report. Things that could be improved.

You can use the search tool to search for information, if that will help you critique the report

Do not write to the `final_report.md` yourself.

Things to check:
- Check that each section is appropriately named
- Check that the report is written as you would find in an essay or a textbook - it should be text heavy, do not let it just be a list of bullet points!
- Check that the report is comprehensive. If any paragraphs or sections are short, or missing important details, point it out.
- Check that the article covers key areas of the industry, ensures overall understanding, and does not omit important parts.
- Check that the article deeply analyzes causes, impacts, and trends, providing valuable insights
- Check that the article closely follows the research topic and directly answers questions
- Check that the article has a clear structure, fluent language, and is easy to understand.
- Check that document sources are properly integrated and cited
"""

critique_sub_agent = {
    "name": "critique-agent",
    "description": "Used to critique the final report. Give this agent some information about how you want it to critique the report.",
    "prompt": sub_critique_prompt,
}

# Load all MCP tools (now includes Unstructured + existing tools)
_mcp_tools = get_all_mcp_tools()

# Create the agent with all capabilities
agent = create_deep_agent(
    [internet_search] + _mcp_tools,
    research_instructions,
    subagents=[critique_sub_agent, research_sub_agent],
).with_config({"recursion_limit": 1000})
```

## Step 7: Final Project Structure

Your complete project structure should look like this:

```
your-project/
├── .env                              # Main project environment
├── research_agent.py                 # Your enhanced research agent
├── deepagents/
│   └── mcp_tools.py                  # Updated with Unstructured integration
├── mcp-unstructured-server/          # Unstructured MCP server
│   ├── .env                          # Server-specific environment
│   ├── doc_processor.py              # MCP server implementation
│   ├── pyproject.toml                # uv project configuration
│   └── .venv/                        # Server virtual environment
├── question.txt                      # Research question storage
├── final_report.md                   # Generated reports
└── /tmp/unstructured_output/         # Processed document outputs
```

## Usage Examples

### Basic Document Processing
```python
# Your agent can now handle requests like:
"Process the PDF at /path/to/contract.pdf and summarize its key terms"

"Analyze the presentation at /path/to/quarterly-results.pptx and research industry benchmarks"
```

### Combined Document + Web Research
```python
"Process the research paper at /path/to/ai-trends-2024.pdf and compare its findings with the latest industry reports from this year"

"Analyze the financial statements in /path/to/company-10k.pdf and research current market conditions affecting this industry"
```

### Multi-Document Analysis
```python
"Process both /path/to/proposal-a.docx and /path/to/proposal-b.docx, then research market rates to recommend the best option"
```

## Key Features & Benefits

### Document Processing Capabilities
- **Multi-Format Support**: 40+ file types including PDF, DOCX, PPTX, images, spreadsheets
- **Structured Extraction**: Preserves formatting, tables, headers, and document hierarchy
- **Metadata Extraction**: Pulls creation dates, authors, and document properties
- **OCR Processing**: Extracts text from images and scanned documents

### Integration Advantages
- **Seamless Workflow**: Documents processed using same tool pattern as web search
- **Combined Intelligence**: Document evidence + current web research in single reports
- **Proper Citations**: Tracks both document sources and web sources
- **Error Handling**: Graceful failures with detailed error messages

### Research Enhancement
- **Evidence-Based Analysis**: Use documents as primary sources, web for current context
- **Comparative Studies**: Compare document data with current market information
- **Historical + Current**: Combine historical document data with latest trends
- **Comprehensive Reports**: Single reports covering both proprietary and public information

## Troubleshooting

### Common Issues & Solutions

#### 1. Server Won't Start
**Symptoms**: `[unstructured_mcp] Failed to start` error
**Solutions**:
- Verify `UNSTRUCTURED_API_KEY` is set correctly
- Check `UNSTRUCTURED_MCP_DIR` points to correct absolute path
- Ensure `uv` is installed and accessible in PATH
- Test the server independently: `cd mcp-unstructured-server && uv run doc_processor.py`

#### 2. File Processing Failures
**Symptoms**: "File does not exist" or processing errors
**Solutions**:
- Use absolute file paths (not relative paths)
- Verify file exists and is readable
- Check file extension is supported (see supported_extensions in code)
- For large files (>400KB), expect longer processing times

#### 3. Import/Dependency Errors
**Symptoms**: ModuleNotFoundError or import failures
**Solutions**:
- Run `uv add "mcp[cli]" "unstructured-client>=0.30.6" python-dotenv` in MCP server directory
- Ensure virtual environment is properly activated
- Check `langchain-mcp-adapters` is installed in main project

#### 4. Connection Timeouts
**Symptoms**: Server connection timeouts or slow responses
**Solutions**:
- Start with smaller files (<400KB) for testing
- Increase timeout settings if processing large documents
- Check network connectivity for API calls
- Monitor API usage limits

### Debugging Steps

1. **Test Individual Components**:
   ```bash
   # Test MCP server directly
   cd mcp-unstructured-server
   uv run doc_processor.py
   
   # Test main project MCP connection
   python -c "from deepagents.mcp_tools import get_unstructured_mcp_tools; print(len(get_unstructured_mcp_tools()))"
   ```

2. **Check Log Output**:
   Look for these patterns in your console:
   ```
   [unstructured_mcp] Starting Unstructured MCP server...
   [unstructured_mcp] Successfully connected! Got X tools
   ```

3. **Verify Environment Variables**:
   ```bash
   echo $UNSTRUCTURED_API_KEY
   echo $UNSTRUCTURED_MCP_DIR
   echo $UNSTRUCTURED_OUTPUT_DIR
   ```

4. **Test File Processing**:
   ```python
   # Test with a simple text file first
   test_file = "/path/to/simple.txt"
   # Then try PDFs and other formats
   ```

## Advanced Configuration

### Custom Output Directory
```python
# In doc_processor.py, modify:
PROCESSED_FILES_FOLDER = os.getenv("UNSTRUCTURED_OUTPUT_DIR", "/your/custom/path")
```

### Processing Options
You can modify the `PartitionRequest` in `doc_processor.py` for advanced options:
```python
req = operations.PartitionRequest(
    partition_parameters=shared.PartitionParameters(
        files=shared.Files(content=open(filepath, "rb"), file_name=filepath),
        strategy=shared.Strategy.AUTO,  # or HI_RES, FAST, OCR_ONLY
        chunking_strategy="by_title",   # Optional: enable chunking
        max_characters=1500,            # Optional: chunk size
        combine_under_n_chars=200,      # Optional: combine small elements
    ),
)
```

### Performance Optimization
- Use `Strategy.FAST` for faster processing of simple documents
- Use `Strategy.HI_RES` for complex documents with tables and images
- Enable chunking for very large documents
- Process multiple files in parallel using research sub-agents

## Next Steps

1. **Test the Integration**: Start with a simple PDF or Word document
2. **Expand Use Cases**: Try different file types and research scenarios  
3. **Customize Processing**: Modify the MCP server for your specific needs
4. **Scale Usage**: Process multiple documents and create comprehensive reports
5. **Monitor Performance**: Track API usage and optimize for your workflow

This integration transforms your research agent into a powerful document analysis tool that combines the best of structured document processing with real-time web research!