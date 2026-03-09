---
name: clinical-trial-search
description: Search and analyze clinical trials
metadata: {"medclaw":{
  "emoji": "🔬",
  "triggers": ["临床试验", "clinical trial", "clinical study", "临床研究"],
  "output": "trial-info",
  "risk": "low",
  "freshness": "realtime",
  "tools": ["med_clinical_trials"],
  "required_tools": ["med_clinical_trials"],
  "domains": ["clinical"],
  "user_levels": ["researcher", "clinician"]}}
---

# Clinical Trial Search

Search and retrieve information about clinical trials.

## When to use

- User wants to find ongoing or completed trials for a condition
- User is looking for eligible trials for patients
- User is researching trial design for a new study

## Workflow

1. Use `med_clinical_trials` to search ClinicalTrials.gov
2. Extract: NCT ID, Title, Phase, Status
3. Extract: Inclusion/Exclusion criteria
4. Extract: Primary outcomes, Sponsor, Locations

## Output format

```md
# Clinical Trials: [CONDITION]

## Summary
- **Total Found**: [N] trials
- **Recruiting**: [N] trials
- **Completed**: [N] trials

## Key Trials

### [Trial Title]
- **NCT ID**: NCT########
- **Phase**: Phase [I/II/III/IV]
- **Status**: [Recruiting/Completed/Active]
- **Sponsor**: [Sponsor Name]
- **Locations**: [Countries/Cities]

### [Another Trial]
...
```

## Style rules

- Always include NCT ID for reference
- Note the recruitment status
- Include phase information
- List locations if relevant to user
