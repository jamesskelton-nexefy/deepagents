# Research Agent Example

This is a comprehensive example of a research agent built with `deepagents` that demonstrates advanced features including sub-agents, file system operations, and RAG (Retrieval Augmented Generation) capabilities.

## Features

- **Internet Search**: Uses Tavily to search the web for research
- **Sub-agents**: 
  - Research sub-agent for conducting focused research
  - Critique sub-agent for reviewing and improving reports
- **RAG Capabilities**: Upload and search through documents (PDF, DOCX, PPTX)
- **File System**: Virtual filesystem for managing research files and reports
- **Planning**: Built-in todo list for tracking research progress

## Setup

### Prerequisites

1. Python 3.11+ with venv
2. API Keys:
   - `TAVILY_API_KEY` for web search
   - `OPENAI_API_KEY` for RAG embeddings (optional, only if using document upload)
   - `ANTHROPIC_API_KEY` for Claude models

### Installation

```bash
# Navigate to the research example directory
cd examples/research

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the `examples/research` directory:

```bash
TAVILY_API_KEY=your_tavily_key_here
OPENAI_API_KEY=your_openai_key_here  # Required for RAG
ANTHROPIC_API_KEY=your_anthropic_key_here
```

## Usage

### Running the Agent

```python
from research_agent import agent

# Basic research query
result = agent.invoke({
    "messages": [{"role": "user", "content": "Research the history of machine learning"}]
})

# With document upload (via frontend)
# 1. Upload documents through the UI
# 2. Agent automatically indexes them
# 3. Agent can then search and reference uploaded documents
result = agent.invoke({
    "messages": [{"role": "user", "content": "Based on the uploaded syllabus, create a course analysis"}],
    "thread_id": "your-thread-id"  # Important for document isolation
})
```

### Streaming Chain of Thought

The research agent supports real-time chain of thought streaming, allowing you to observe the agent's reasoning process as it works:

```python
# Stream the agent's thinking process
async for chunk in agent.astream(
    {"messages": [{"role": "user", "content": "Research machine learning"}]},
    stream_mode=["updates", "messages", "custom"]
):
    # Stream modes provide different insights:
    # - "updates": See todos being created, files being written
    # - "messages": Observe LLM reasoning tokens in real-time
    # - "custom": Track sub-agent invocations and their reasoning
    pass
```

**Frontend Integration:**
The frontend automatically displays:
- Main agent thinking in collapsible "Thinking..." blocks
- Sub-agent reasoning nested under "Research Agent" or "Critique Agent" labels
- Tool calls with status indicators
- Real-time streaming text updates

This provides transparency into:
- When the research sub-agent is invoked and what it's researching
- The critique sub-agent's feedback as it reviews the report
- File operations and planning decisions
- Internet searches and document retrieval operations

### RAG Features

The research agent includes built-in RAG capabilities:

#### Document Upload
- Supports PDF, DOCX, and PPTX files
- Automatically chunks documents (1000 characters with 200 character overlap)
- Indexes using OpenAI embeddings
- Stores in per-thread vector stores (documents isolated by conversation)

#### Semantic Search
The agent can use the `retrieve_context` tool to search through uploaded documents:

```python
# The agent will automatically use this when appropriate
# Example user query: "What learning objectives are mentioned in the uploaded syllabus?"
# The agent will:
# 1. Use retrieve_context(query="learning objectives")
# 2. Get relevant document chunks
# 3. Use that context to answer the question
```

#### Document Parsing

You can also parse documents directly using the command-line tool:

```bash
# Parse a document and index it
python document_parser.py path/to/document.pdf thread-id-123

# With specific extension
python document_parser.py path/to/document.pdf thread-id-123 --extension pdf
```

## Agent Instructions

The research agent is configured to:

1. Write the research topic to a file (`topic.txt`)
2. Check for uploaded documents and search them if available
3. Use the research sub-agent to conduct deep research
4. Write a comprehensive Instructional Design Analysis Report
5. Use the critique sub-agent to review and improve the report
6. Iterate until satisfied with the quality

## Output

The agent produces:
- `topic.txt`: The research topic
- `Instructional_Design_Analysis_Report.md`: The final comprehensive report
- Any intermediate research files

The report includes:
- Executive Summary
- Project Context & Stakeholder Information
- Learning Needs Analysis
- Learner Analysis & Personas
- Content Analysis
- Learning Objectives & Outcomes
- Task Analysis
- Contextual Analysis
- Gap Analysis
- Instructional Strategy Recommendations
- Assessment Strategy
- Sources (with citations)

## Customization

### Adjust RAG Parameters

In `tools.py`, you can modify:
- `chunk_size`: Size of document chunks (default: 1000)
- `chunk_overlap`: Overlap between chunks (default: 200)
- `k`: Number of chunks to retrieve (default: 2)

### Change Embeddings Model

In `vector_store.py`, you can change the embeddings model:

```python
self._embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large"  # or "text-embedding-3-small", etc.
)
```

### Modify Agent Instructions

Edit `research_instructions` in `research_agent.py` to customize:
- Research methodology
- Report structure
- Tool usage guidance
- RAG behavior

## Troubleshooting

### No documents found
- Ensure `OPENAI_API_KEY` is set
- Verify the `thread_id` matches between upload and retrieval
- Check that documents were successfully uploaded and parsed

### Python script not found
- Ensure you're running from the correct directory
- Check that the venv is activated
- Verify the Python path in `upload-document/route.ts` matches your setup

### Memory issues with large documents
- Reduce `chunk_size` for smaller chunks
- Increase `chunk_overlap` for better context preservation
- Process fewer documents per thread

## Architecture

```
Frontend (Next.js)
  ↓ uploads document
API Route (/api/upload-document)
  ↓ saves temp file
Document Parser (document_parser.py)
  ↓ chunks & indexes
Vector Store Manager (per-thread)
  ↓ stores embeddings
Agent uses retrieve_context tool
  ↓ semantic search
Returns relevant context
```

## Testing

Run the RAG tests:

```bash
pytest tests/test_rag.py -v
```

## License

See the main repository LICENSE file.

