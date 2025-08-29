import os
from typing import Literal

from tavily import TavilyClient
from dotenv import load_dotenv

from deepagents import create_deep_agent, SubAgent
from deepagents.mcp_tools import get_all_mcp_tools
import os
import requests
 
# It's best practice to initialize the client once and reuse it.
# Load environment variables from the project root .env file
# This ensures UNSTRUCTURED_API_KEY and related vars are available
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
"""

critique_sub_agent = {
    "name": "critique-agent",
    "description": "Used to critique the final report. Give this agent some infomration about how you want it to critique the report.",
    "prompt": sub_critique_prompt,
}


# Prompt prefix to steer the agent to be an expert researcher
research_instructions = """You are an expert researcher with advanced document processing capabilities. Your job is to conduct thorough research and write a polished report.

The first thing you should do is to write the original user question to `question.txt` so you have a record of it.

Use the research-agent to conduct deep research. It will respond to your questions/topics with a detailed answer.

## Available Tools:

### Core Research Tools:
1. internet_search - Web search for current information and trends
2. process_document - Process local documents (PDF, DOCX, PPT, images, etc.) using Unstructured AI to extract structured text, tables, and metadata
3. list_documents_with_context - List all documents in the current conversation context
4. search_documents_with_context - Search through processed documents using semantic search within the current context
5. retrieve_document - Retrieve full content of a specific document by ID or filename (requires context_id parameter)
6. process_agent_document - Process approved VFS documents through Supabase ingest pipeline to make them searchable

**Important**: The document tools (list_documents_with_context, search_documents_with_context, process_agent_document) automatically use the contextId from the conversation state. The retrieve_document tool still requires an explicit context_id parameter.
7. research-agent - Delegate specific research topics to specialized sub-agents
8. critique-agent - Get detailed feedback and suggestions for improving your reports

When you think you enough information to write a final report, write it to `final_report.md`

You can call the critique-agent to get a critique of the final report. After that (if needed) you can do more research and edit the `final_report.md`
You can do this however many times you want until are you satisfied with the result.

Only edit the file once at a time (if you call this tool in parallel, there may be conflicts).

### Document Processing Workflow:
When users provide documents or ask you to analyze files:

1. List Available Documents: Use list_documents_with_context() to see what documents are already processed in the current conversation context.
2. Extract Document Content: Use process_document(filepath="/absolute/path/to/document") to extract structured content
3. Search Documents: Use search_documents_with_context(query="your query") for semantic search through processed documents in the current context
4. Retrieve Documents: Use retrieve_document(document_id="doc-id" or filename="file.pdf", context_id="your-context-id") to get full document content
5. Process Agent Documents: Use process_agent_document(vfs_file_path="/path/to/file", approved_filename="report.md") to process approved VFS documents so they become searchable within the conversation context
6. Analyze Structure: The tools extract titles, headers, paragraphs, tables, lists, and metadata
7. Integrate with Research: Combine document insights with web research for comprehensive analysis
8. Reference Sources: Include both document findings and web sources in your citations

### Supported File Types:
- Documents: PDF, DOCX, DOC, ODT, RTF, TXT, MD
- Presentations: PPTX, PPT, ODP
- Spreadsheets: XLSX, XLS, CSV
- Images: PNG, JPG, JPEG, TIFF, BMP, SVG
- Web: HTML, HTM, XML
- Email: EML

Here are instructions for writing the final report:

<report_instructions>

CRITICAL: Make sure the answer is written in the same language as the human messages! If you make a todo plan - you should note in the plan what language the report should be in so you dont forget!
Note: the language the report should be in is the language the QUESTION is in, not the language/country that the question is ABOUT.

Please create a detailed answer to the overall research brief that:
1. Is well-organized with proper headings (# for title, ## for sections, ### for subsections)
2. Includes specific facts and insights from the research
3. References relevant sources using [Title](URL) format
4. Provides a balanced, thorough analysis. Be as comprehensive as possible, and include all information that is relevant to the overall research question. People are using you for deep research and will expect detailed, comprehensive answers.
5. Includes a "Sources" section at the end with all referenced links

You can structure your report in a number of different ways. Here are some examples:

To answer a question that asks you to compare two things, you might structure your report like this:
1/ intro
2/ overview of topic A
3/ overview of topic B
4/ comparison between A and B
5/ conclusion

To answer a question that asks you to return a list of things, you might only need a single section which is the entire list.
1/ list of things or table of things
Or, you could choose to make each item in the list a separate section in the report. When asked for lists, you don't need an introduction or conclusion.
1/ item 1
2/ item 2
3/ item 3

To answer a question that asks you to summarize a topic, give a report, or give an overview, you might structure your report like this:
1/ overview of topic
2/ concept 1
3/ concept 2
4/ concept 3
5/ conclusion

If you think you can answer the question with a single section, you can do that too!
1/ answer

REMEMBER: Section is a VERY fluid and loose concept. You can structure your report however you think is best, including in ways that are not listed above!
Make sure that your sections are cohesive, and make sense for the reader.

For each section of the report, do the following:
- Use simple, clear language
- Use ## for section title (Markdown format) for each section of the report
- Do NOT ever refer to yourself as the writer of the report. This should be a professional report without any self-referential language. 
- Do not say what you are doing in the report. Just write the report without any commentary from yourself.
- Each section should be as long as necessary to deeply answer the question with the information you have gathered. It is expected that sections will be fairly long and verbose. You are writing a deep research report, and users will expect a thorough answer.
- Use bullet points to list out information when appropriate, but by default, write in paragraph form.

REMEMBER:
The brief and research may be in English, but you need to translate this information to the right language when writing the final answer.
Make sure the final answer report is in the SAME language as the human messages in the message history.

Format the report in clear markdown with proper structure and include source references where appropriate.

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Each source should be a separate line item in a list, so that in markdown it is rendered as a list.
- Example format:
  [1] Source Title: URL
  [2] Source Title: URL
- Citations are extremely important. Make sure to include these, and pay a lot of attention to getting these right. Users will often use these citations to look into more information.
</Citation Rules>
</report_instructions>

You have access to a few tools.

## `internet_search`

Use this to run an internet search for a given query. You can specify the number of results, the topic, and whether raw content should be included.
"""

# Load all MCP tools (Firecrawl + Microsoft Learn + Unstructured)
_mcp_tools = get_all_mcp_tools()

# Import consolidated document tools
from deepagents.tools import (
    list_documents_with_context,
    search_documents_with_context,
    process_agent_document,
    retrieve_document
)

# Create the agent
# Edge Function backed tools
def search_documents(query: str, context_id: str, top_k: int = 5):
    """Search processed documents within a context using the rag_search Edge Function.

    Args:
        query: Natural language query to embed and search.
        context_id: The context UUID to scope retrieval to.
        top_k: Maximum number of matches to return (default 5).

    Returns:
        JSON object with a 'matches' array of chunk hits and metadata.
    """
    url = os.environ.get("SUPABASE_URL", "").rstrip("/") + "/functions/v1/rag_search"
    key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    resp = requests.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json={"context_id": context_id, "query": query, "top_k": top_k})
    resp.raise_for_status()
    return resp.json()

def retrieve_document(document_id: str = "", context_id: str = "", filename: str = "", version: int | None = None, format: str = "text"):
    """Retrieve a full document's content or original file via Edge Function.

    Provide either a document_id, or a (context_id, filename[, version]) tuple.

    Args:
        document_id: The document UUID to fetch (if known).
        context_id: Context UUID when resolving by filename.
        filename: Document filename to resolve (used with context_id).
        version: Optional version number; defaults to latest when omitted.
        format: One of 'text' (text_content), 'json' (raw_json), or 'original' (signed URL).

    Returns:
        JSON payload containing the requested representation of the document.
    """
    url = os.environ.get("SUPABASE_URL", "").rstrip("/") + "/functions/v1/retrieve_document"
    key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    # Validate inputs
    allowed_formats = {"text", "json", "original"}
    if format not in allowed_formats:
        format = "text"
    if not document_id and not (context_id and filename):
        raise ValueError("Provide either document_id or (context_id and filename)")

    payload = {"format": format}
    if document_id:
        payload.update({"document_id": document_id})
    else:
        payload.update({"context_id": context_id, "filename": filename})
        if version is not None:
            payload.update({"version": version})
    resp = requests.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload)
    resp.raise_for_status()
    return resp.json()

# Create the agent with consolidated tools
agent = create_deep_agent(
    [
        internet_search, 
        search_documents_with_context,  # Use context-aware version
        retrieve_document,  # Keep original (it already takes context_id)
        list_documents_with_context,    # Use context-aware version
        process_agent_document          # Process approved VFS documents
    ] + _mcp_tools,
    research_instructions,
    subagents=[critique_sub_agent, research_sub_agent],
).with_config({"recursion_limit": 1000})
