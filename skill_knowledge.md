# Anthropic Agent Skills — Knowledge Base

> Consolidated guidance for understanding, authoring, and using Agent Skills across Claude surfaces. Includes TL;DR, deep dive, examples, constraints, and security.

## TL;DR

- Agent Skills are filesystem-based folders that package domain expertise as instructions, linked references, and optional scripts. Claude discovers them via YAML metadata and loads content progressively when relevant. [Overview](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview), [Engineering blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- Progressive disclosure levels:
  - Level 1: `name` and `description` metadata preloaded in the system prompt.
  - Level 2: `SKILL.md` instructions loaded when the skill is triggered.
  - Level 3+: linked files/resources read as needed; scripts can be executed deterministically without loading their source. [Overview](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
- Where Skills work: Claude API (pre-built + custom), Claude Code (custom, filesystem-based), Claude.ai (pre-built + custom via upload; per-user). Skills do not auto-sync across surfaces. [Overview](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
- Runtime constraints (API): no network access, no runtime package install; only pre-installed dependencies. Prefer executable scripts for deterministic operations and token efficiency. [Overview](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
- Authoring: be concise; design for progressive disclosure; use clear names/descriptions; organize by domain; keep references one-level deep; provide validation workflows and utility scripts. [Best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)

---

## Core concepts

### Anatomy of a Skill

- A Skill is a directory with a required `SKILL.md` that begins with YAML frontmatter containing exactly two fields:
  - `name` (≤ 64 chars)
  - `description` (≤ 1024 chars; include what it does and when to use)  
  [Overview → Skill structure](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview#skill-structure), [Best practices → YAML frontmatter requirements](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices#yaml-frontmatter-requirements)

Minimal skeleton:

```markdown
---
name: "PDF Processing"
description: "Extract text and tables, fill forms, merge PDFs. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction."
---

# PDF Processing

## Quick start
Use pdfplumber for text extraction.

## Advanced guidance
See FORMS.md for form filling; REFERENCE.md for APIs; scripts/ for utilities.
```

- As skills grow, split content into separate files and link them from `SKILL.md` (one level deep). [Best practices → Progressive disclosure patterns](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices#progressive-disclosure-patterns)

### Progressive disclosure

| Level | When loaded | Token cost | Content |
| --- | --- | --- | --- |
| 1: Metadata | Startup | Small (~100 tokens/skill) | YAML: `name`, `description` |
| 2: Instructions | When triggered | Limited (aim < 500 lines) | `SKILL.md` procedural guidance |
| 3+: Resources & code | As needed | Effectively unbounded | Linked markdown, assets, and executable scripts |

- Claude reads files via bash only when needed and can execute scripts without loading source code into context (only outputs consume tokens).  
  [Overview → How Skills work](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview#how-skills-work), [Engineering blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

### Architecture and environment

- Filesystem-based; Claude navigates your skill like a directory and reads specific files on-demand.  
- Deterministic scripts: bundle utilities (e.g., `scripts/fill_form.py`) and tell Claude when to run vs read as reference.  
- API code execution container constraints:  
  - No network access  
  - No runtime package installation  
  - Pre-configured dependencies only  
  [Overview → Runtime environment constraints](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview#runtime-environment-constraints)

---

## Where Skills work

- Claude API: pre-built skills (e.g., `pptx`, `xlsx`, `docx`, `pdf`) and custom skills; specify allowed skills via `container.skills` and enable the code execution tool (with the required beta headers noted in docs).  
  [Quickstart](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/quickstart), [Overview → Where Skills work](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview#where-skills-work)
- Claude Code: supports custom, filesystem-based skills (personal `~/.claude/skills/`, project `.claude/skills/`).  
  [Overview → Claude Code](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview#claude-code)
- Claude.ai: pre-built skills available by default; upload custom skills (zip) via settings; per-user scope.  
  [Overview → Claude.ai](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview#claude-ai)

Cross-surface availability: Skills do not auto-sync between API, Claude.ai, and Claude Code; manage and upload separately.  
[Overview → Cross-surface availability](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview#cross-surface-availability)

---

## Using pre-built Skills via the API (example)

Python (from the Quickstart):

```python
import anthropic

client = anthropic.Anthropic()

response = client.beta.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    betas=["code-execution-2025-08-25", "skills-2025-10-02"],
    container={
        "skills": [
            {"type": "anthropic", "skill_id": "pptx", "version": "latest"}
        ]
    },
    messages=[{"role": "user", "content": "Create a 5-slide presentation on renewable energy"}],
    tools=[{"type": "code_execution_20250825", "name": "code_execution"}]
)
```

- Then retrieve generated files via the Files API using the returned `file_id`.  
  [Quickstart](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/quickstart)

Pre-built skills available: `pptx`, `xlsx`, `docx`, `pdf`.  
[Quickstart](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/quickstart)

---

## Authoring best practices

- Conciseness: the context window is shared; keep `SKILL.md` under ~500 lines; move details into linked files.  
- One-level references: link reference files directly from `SKILL.md` (avoid deep chains).  
- Clear discovery: write specific `description` with triggers (what + when). Use consistent terminology and gerund-style names (e.g., “Processing PDFs”).  
- Degrees of freedom: choose specificity based on task fragility (high/medium/low freedom).  
- Workflows and feedback loops: provide checklists; add verifiable intermediate outputs (e.g., plan → validate script → execute → verify).  
- Utility scripts: pre-bundle scripts for deterministic operations; make execution intent explicit.  
- Pathing: always use forward slashes; descriptive filenames; organize by domain.  
- Testing: build evaluations first; test with Haiku/Sonnet/Opus; iterate from observation of real usage.  
[Best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)

Example directory:

```text
pdf/
├─ SKILL.md              # Main instructions (loaded when triggered)
├─ FORMS.md              # Form-filling guide (loaded as needed)
├─ reference.md          # API reference (loaded as needed)
└─ scripts/
   └─ fill_form.py       # Executed as a tool; only outputs enter context
```

---

## Security considerations

- Treat Skills like software installs: audit all bundled files (markdown, scripts, assets).  
- Be cautious with external fetches and tool invocations; avoid time-sensitive or risky dependencies.  
- Consider data exposure risk when Skills access sensitive content.  
[Engineering blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), [Overview → Security considerations](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview#security-considerations)

---

## FAQ and gotchas

- Do Skills sync across surfaces? No—manage separately for API, Claude.ai, and Claude Code.  
- Can I install packages at runtime (API)? No; only pre-installed packages are available.  
- How deep should references go? One level from `SKILL.md` to avoid partial reads.  
- What should go in `description`? Both what the Skill does and when to use it; third-person tone.  
- How big can a Skill be? Bundled content can be large; token cost occurs only when files are read.  
[Overview](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview), [Best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)

---

## Example: PDF skill pattern

- Provide minimal quick-start in `SKILL.md`, link `FORMS.md` for conditional form filling, keep detailed API notes in `reference.md`, and include scripts in `scripts/` for deterministic operations (e.g., field extraction, validation).  
[Engineering blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

---

## References

- Engineering blog — Equipping agents for the real world with Agent Skills:  
  https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Docs — Agent Skills overview:  
  https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview
- Docs — Quickstart:  
  https://docs.claude.com/en/docs/agents-and-tools/agent-skills/quickstart
- Docs — Best practices:  
  https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices
