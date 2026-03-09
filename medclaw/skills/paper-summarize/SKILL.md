---
name: paper-summarize
description: Extract and summarize key points from a medical research paper
metadata: {"medclaw":{
  "emoji": "📄",
  "triggers": ["论文总结", "paper summary", "abstract extraction", "论文摘要"],
  "output": "paper-summary",
  "risk": "low",
  "freshness": "realtime",
  "tools": ["med_pubmed_search", "med_pmc_fulltext"],
  "required_tools": ["med_pubmed_search"],
  "domains": ["clinical", "basic", "translational"],
  "user_levels": ["medical_student", "researcher", "clinician"]}}
---

# Paper Summary

Extract and summarize key points from a medical research paper.

## When to use

- User provides a PMID or DOI and wants a quick summary
- User wants to understand a paper's main findings
- User is screening papers for a literature review

## Workflow

1. Get the paper details using PMID or DOI
2. Extract: Title, Authors, Journal, Year
3. Extract: Abstract, Methods, Results, Conclusions
4. Identify: Study design, Sample size, Key findings

## Output format

```md
# Paper Summary: [TITLE]

## Basic Info
- **PMID/DOI**: [ID]
- **Journal**: [Journal Name]
- **Year**: [Year]
- **Authors**: [First Author et al.]

## Abstract
[Key points from abstract]

## Study Design
[Type of study, sample size, duration]

## Key Findings
1. [Finding 1]
2. [Finding 2]
3. [Finding 3]

## Limitations
- [Limitation 1]
- [Limitation 2]

## Clinical Relevance
[How this impacts clinical practice]
```

## Style rules

- Be concise but comprehensive
- Accurately represent the authors' conclusions
- Note any potential conflicts of interest
- Include PMID/DOI for verification
