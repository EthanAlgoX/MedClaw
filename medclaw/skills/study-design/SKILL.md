---
name: study-design
description: Provide guidance on clinical study design
metadata: {"medclaw":{
  "emoji": "📋",
  "triggers": ["研究设计", "study design", "study methodology", "研究方法"],
  "output": "design-guidance",
  "risk": "low",
  "freshness": "realtime",
  "tools": ["med_pubmed_search"],
  "required_tools": [],
  "domains": ["clinical", "translational"],
  "user_levels": ["researcher"]}}
---

# Study Design

Provide guidance on clinical and translational study design.

## When to use

- User is planning a new research study
- User needs advice on appropriate methodology
- User wants to understand study design options

## Common Designs

### Observational Studies
- **Cohort Study**: Follow exposed vs unexposed over time
- **Case-Control Study**: Compare cases with controls retroactively
- **Cross-Sectional Study**: Snapshot at one time point

### Experimental Studies
- **Randomized Controlled Trial (RCT)**: Gold standard
- **Cluster Randomized Trial**: Randomize groups
- **Crossover Trial**: Participants serve as own controls

## Key Considerations

1. **Research Question**: Clear, specific, answerable
2. **Population**: Define inclusion/exclusion criteria
3. **Sample Size**: Power calculation required
4. **Outcomes**: Primary and secondary endpoints
5. **Statistical Analysis**: Pre-specified analysis plan

## Output format

```md
# Study Design Guidance: [TOPIC]

## Recommended Design
[Based on the research question]

## Key Elements
### Population
[Who to include]

### Sample Size
[Power calculation approach]

### Outcomes
- Primary: [Outcome]
- Secondary: [Outcomes]

### Statistical Plan
[Analysis approach]

## Strengths and Limitations
[Pros and cons of the recommended design]

## Alternatives
[Other designs to consider]
```
