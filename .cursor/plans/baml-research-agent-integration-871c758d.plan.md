<!-- 871c758d-29e2-4ba9-86cf-767645873a5e f309391d-b0d9-4d79-ab27-02c41e74a642 -->
# BAML Integration for Research Agent Report Consistency

## Current State Analysis

The research agent (`examples/research/research_agent.py`) currently uses **200+ lines of prompt instructions** (lines 86-223) to define the Instructional Design Analysis Report structure. This approach has several limitations:

- No type safety - the LLM can deviate from the expected structure
- Difficult to validate that all required sections are present
- Multiple agent variants (research_agent.py, lxd.py, learning_design.py) with inconsistent structures
- Citation formatting relies solely on prompt engineering
- No programmatic way to ensure fields are populated correctly

## BAML Solution Overview

BAML will provide:

1. **Type-safe report schemas** - Define report structure as BAML classes
2. **Automatic validation** - BAML's parser validates LLM output matches schema
3. **Better error handling** - Retry logic when structure deviates
4. **Consistent structure** - Single source of truth for all report types
5. **Streaming support** - Type-safe streaming with `partial_types` module
6. **Native testing** - BAML's built-in test framework in .baml files

## Implementation Plan

### 1. Install BAML Dependencies

Add to `examples/research/requirements.txt`:

```
baml-py>=0.211.0
```

Install BAML VSCode extension for interactive testing and development.

### 2. Create BAML Schema Files

Create `examples/research/baml_src/` directory structure:

```
baml_src/
├── main.baml                    # Report structure types and functions
├── clients.baml                 # LLM client configurations
├── generators.baml              # Python client generator config
└── tests.baml                   # BAML native tests (optional separate file)
```

**Key BAML Types to Define:**

**`main.baml`** - Define the complete report structure:

```baml
class Citation {
  number int
  title string
  url string
}

class ExecutiveSummary {
  project_overview string
  key_findings string[]
  critical_recommendations string[]
  timeline_overview string
}

class ProjectContext {
  organizational_background string
  project_sponsors string[]
  business_drivers string[]
  success_criteria string[]
}

// ... define all 13 sections similarly ...

class InstructionalDesignReport {
  title string
  executive_summary ExecutiveSummary
  project_context ProjectContext
  learning_needs_analysis LearningNeedsAnalysis
  learner_analysis LearnerAnalysis
  learner_personas LearnerPersonas
  content_analysis ContentAnalysis
  learning_objectives LearningObjectives
  task_analysis TaskAnalysis
  contextual_analysis ContextualAnalysis
  gap_analysis GapAnalysis
  instructional_strategy InstructionalStrategy
  assessment_strategy AssessmentStrategy
  sources Citation[]
}

function GenerateReport(
  topic: string,
  research_data: string,
  language: string
) -> InstructionalDesignReport {
  client "openai/gpt-4o"
  prompt #"
    You are an expert researcher in elearning course creation.
    
    Topic: {{ topic }}
    Language: {{ language }}
    
    Research Data:
    {{ research_data }}
    
    {{ ctx.output_format }}
    
    Generate a comprehensive Instructional Design Analysis Report.
  "#
}
```

### 3. Configure LLM Clients

**`clients.baml`**:

```baml
client<llm> GPT4 {
  provider "openai"
  options {
    model "gpt-4o"
    temperature 0.7
    max_tokens 4096
  }
}

client<llm> Claude {
  provider "anthropic"
  options {
    model "claude-3-5-sonnet-20241022"
    temperature 0.7
    max_tokens 4096
  }
}

// Fallback strategy
client<llm> ReportGenerator {
  provider "fallback"
  options {
    strategy [GPT4, Claude]
  }
}
```

### 4. Set Up Generator Config

**`generators.baml`**:

```baml
generator python {
  output_type python/pydantic
  output_dir "../"
  version "0.211.0"
}
```

### 5. Create BAML Native Tests

**CRITICAL:** BAML uses its own testing framework. Tests are written **inside `.baml` files**, not Python!

Add to **`baml_src/main.baml`** or create **`baml_src/tests.baml`**:

```baml
// Test: Report has all required sections
test TestReportStructure {
  functions [GenerateReport]
  args {
    topic "Python Programming Basics"
    research_data #"
      Python is a high-level programming language.
      Created by Guido van Rossum in 1991.
      Known for simple syntax.
      Source: https://python.org
    "#
    language "English"
  }
  
  // Assert all required sections are present
  @@assert({{ this.title != "" }})
  @@assert({{ this.executive_summary.project_overview != "" }})
  @@assert({{ this.project_context.organizational_background != "" }})
  @@assert({{ len(this.sources) > 0 }})
}

// Test: Citations are properly formatted
test TestCitationFormat {
  functions [GenerateReport]
  args {
    topic "Machine Learning"
    research_data #"
      Machine learning is a subset of AI.
      Source: https://example.com/ml
      Deep learning uses neural networks.
      Source: https://example.com/dl
    "#
    language "English"
  }
  
  @@check({{ this.sources[0].number == 1 }})
  @@check({{ len(this.sources) >= 1 }})
  @@assert({{ all([s.url != "" for s in this.sources]) }})
}

// Test: Multi-language support
test TestSpanishReport {
  functions [GenerateReport]
  args {
    topic "Inteligencia Artificial"
    research_data "La IA es el futuro. Fuente: https://example.com"
    language "Spanish"
  }
  
  @@assert({{ this.title != "" }})
}
```

**Running BAML Tests:**

```bash
# From examples/research directory
baml-cli test                    # Run all tests
baml-cli test --filter TestReportStructure  # Run specific test
baml-cli test --concurrency 4    # Run in parallel
baml-cli test --list             # List tests without running
```

Tests can also be run interactively in VSCode BAML playground with live results.

### 6. Refactor Research Agent

Update `examples/research/research_agent.py`:

**Current (lines 71-230):** Long prompt with structure instructions

**New approach:**

```python
from baml_client import b
from baml_client.types import InstructionalDesignReport

# Simplified prompt - structure is now defined in BAML
research_instructions = """You are an expert researcher in elearning course creation.

1. Write the topic to `topic.txt`
2. Read any provided base content
3. Use research-agent for deep research
4. When ready, generate the report using the structured format
5. Use critique-agent for feedback and iterate

The report structure is enforced by the type system, so focus on quality content.
"""

# Call BAML function instead of manual markdown generation
async def generate_structured_report(topic: str, research_data: str, language: str):
    report = await b.GenerateReport(
        topic=topic,
        research_data=research_data,
        language=language
    )
    return report

# Convert BAML report to markdown for file output
def report_to_markdown(report: InstructionalDesignReport) -> str:
    md = f"# {report.title}\n\n"
    md += f"## Executive Summary\n\n"
    md += f"{report.executive_summary.project_overview}\n\n"
    # ... generate full markdown from structured report
    return md
```

### 7. Add Streaming Support (Optional)

BAML provides native streaming with type-safe partial objects via auto-generated `partial_types` module.

**Update `baml_src/main.baml`** to add streaming attributes:

```baml
class Citation {
  number int @stream.done  // Only stream when complete
  title string
  url string
}

class ExecutiveSummary {
  project_overview string @stream.with_state  // Include streaming state metadata
  key_findings string[]
  critical_recommendations string[]
  timeline_overview string
}

class InstructionalDesignReport {
  title string @stream.not_null  // Must be present for object to stream
  executive_summary ExecutiveSummary
  // ... other sections
  sources Citation[]
}
```

**Streaming Attributes:**

- `@stream.done` - Only streams when fully complete (atomic)
- `@stream.not_null` - Containing object only streams when this field has value
- `@stream.with_state` - Adds metadata to track if field is done streaming

**Python Streaming Implementation:**

```python
from baml_client import b
from baml_client.partial_types import PartialInstructionalDesignReport

async def generate_report_stream(topic: str, research_data: str, language: str):
    """Stream report generation with partial updates"""
    stream = b.stream.GenerateReport(  # Note: b.stream.FunctionName syntax
        topic=topic,
        research_data=research_data,
        language=language
    )
    
    async for partial_report in stream:
        # partial_report is PartialInstructionalDesignReport
        # All fields are Optional except those marked @stream.not_null
        # Number fields only appear when complete (not partial numbers)
        
        if partial_report.title:
            print(f"Title: {partial_report.title}")
        
        if partial_report.executive_summary:
            summary = partial_report.executive_summary
            if summary.project_overview:
                print(f"Overview: {summary.project_overview}")
        
        yield partial_report
    
    # Get final complete report
    final_report = await stream.get_final_response()
    return final_report
```

**Key Streaming Facts:**

1. BAML auto-generates `partial_types` module with nullable fields
2. Numbers only stream when complete (never partial like `1`, `12`, `129`...)
3. Use streaming attributes to enforce semantic validity
4. Syntax is `b.stream.FunctionName()` not `b.FunctionName().stream()`

### 8. Optional Python Integration Tests

While BAML handles prompt testing natively, you may want Python tests for agent workflow:

**`examples/research/test_agent_integration.py`**:

```python
import pytest
from baml_client import b
from baml_client.types import InstructionalDesignReport

@pytest.mark.asyncio
async def test_agent_workflow():
    """Integration test for full agent workflow"""
    report = await b.GenerateReport(
        topic="Python Basics",
        research_data="Test data",
        language="English"
    )
    
    # Type checking (guaranteed by BAML)
    assert isinstance(report, InstructionalDesignReport)
    
    # Convert to markdown
    markdown = report_to_markdown(report)
    assert "# " in markdown  # Has title
    assert "## " in markdown  # Has sections
```

### 9. Update README Documentation

Add section to `examples/research/README.md`:

````markdown
## BAML Integration

This research agent uses BAML for type-safe report generation:

- Report structure defined in `baml_src/main.baml`
- Automatic validation of LLM outputs
- Type-safe Python client generated automatically

### Testing

BAML uses native test blocks in .baml files:

```bash
# Run all BAML tests
baml-cli test

# Run specific test
baml-cli test --filter TestReportStructure

# Interactive testing in VSCode
# Open any .baml file and click "Run Test" in the playground
````

### Regenerating Client

After schema changes:

```bash
cd examples/research
baml-cli generate
```

## Benefits Over Prompt-Based Structure

1. **Type Safety**: Compile-time checks for report structure
2. **Consistency**: Single source of truth for all report types
3. **Validation**: Automatic validation of required fields
4. **Better DX**: VSCode playground for testing report generation
5. **Error Handling**: Built-in retry logic for malformed outputs
6. **Native Testing**: Tests written in BAML, run in VSCode or CLI
7. **Streaming**: Type-safe streaming with partial objects

```

## Files to Modify

- `examples/research/requirements.txt` - Add BAML dependency
- `examples/research/research_agent.py` - Integrate BAML functions (lines 71-237)
- `examples/research/lxd.py` - Update to use shared BAML types
- `examples/research/learning_design.py` - Update to use shared BAML types

## Files to Create

- `examples/research/baml_src/main.baml` - Report structure types, functions, and tests
- `examples/research/baml_src/clients.baml` - LLM client configs
- `examples/research/baml_src/generators.baml` - Python generator config
- `examples/research/test_agent_integration.py` - Optional Python integration tests
- `examples/research/README.md` - Documentation (if doesn't exist)

## Expected Benefits

1. **Consistency** - All three research agent variants will use the same report structure
2. **Type Safety** - IDE autocomplete and compile-time validation
3. **Better Error Handling** - BAML's parser fixes broken JSON and validates structure
4. **Faster Iteration** - Use VSCode playground to test report generation without running the agent
5. **Maintainability** - Report structure is self-documenting and easy to modify
6. **Validation** - Programmatic checks that all required sections are present
7. **Native Testing** - BAML's built-in testing framework ensures reliability
8. **Streaming** - Type-safe streaming with partial objects via `partial_types` module

## Considerations

1. **Learning Curve** - Team needs to learn BAML syntax (similar to TypeScript/Python)
2. **Build Step** - Need to run `baml-cli generate` after schema changes (can be automated)
3. **Migration** - Existing prompts need to be refactored to use BAML functions
4. **Testing Approach** - Tests are written in .baml files, not Python (different from pytest)
5. **VSCode Extension** - Install BAML VSCode extension for best development experience
6. **Streaming API** - Syntax is `b.stream.FunctionName()` - BAML generates `partial_types` module automatically