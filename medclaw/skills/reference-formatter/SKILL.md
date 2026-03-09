---
name: reference-formatter
description: Format references in various citation styles
metadata: {"medclaw":{
  "emoji": "📖",
  "triggers": ["参考文献", "citation format", "reference", "引用格式"],
  "output": "formatted-reference",
  "risk": "low",
  "freshness": "realtime",
  "tools": [],
  "required_tools": [],
  "domains": ["clinical", "basic", "translational"],
  "user_levels": ["medical_student", "researcher", "clinician"]}}
---

# Reference Formatter

Format references in various citation styles.

## Supported Styles

- **Vancouver** (Numbered)
- **APA** (Author-Date)
- **Harvard**
- **AMA** (American Medical Association)
- **MLA**

## Input Format

Provide either:
1. PMID/DOI
2. Raw citation info (authors, title, journal, year, volume, pages)

## Output Format

```md
# Formatted Reference

## Vancouver (Numbered)
[Formatted citation]

## APA
[Formatted citation]

## Harvard
[Formatted citation]
```

## Example

Input: PMID 12345678

Output:
- Vancouver: Smith JA, Jones B. Title of the article. Journal Name. 2023;45(2):123-130.
- APA: Smith, J. A., & Jones, B. (2023). Title of the article. Journal Name, 45(2), 123-130.
