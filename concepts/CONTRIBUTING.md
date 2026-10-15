# Contributing to the SDAT Knowledge Base

## Concept File Schema

Each concept file is a Markdown file with YAML frontmatter:

```yaml
---
id: unique.concept.id
category: category-name
name: Human Readable Name
owning_agent: A-01
maturity: stable | emerging | deprecated
languages: [python, typescript, go]
tags: [tag1, tag2, tag3]
related: [related.concept.id]
---
```

## Agent Ownership

Each concept must have an `owning_agent` field mapping to an agent in `config/agents/`.

## Review Criteria

1. Frontmatter is valid YAML with all required fields
2. Content covers all 7 sections
3. Code examples are language-appropriate
4. Detection signals are defined
