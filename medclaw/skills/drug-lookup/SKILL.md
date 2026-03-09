---
name: drug-lookup
description: Look up drug information including indications, dosage, and side effects
metadata: {"medclaw":{
  "emoji": "💊",
  "triggers": ["药物查询", "drug info", "drug lookup", "药品信息"],
  "output": "drug-info",
  "risk": "medium",
  "freshness": "monthly",
  "tools": ["med_drug_lookup"],
  "required_tools": ["med_drug_lookup"],
  "domains": ["clinical"],
  "user_levels": ["medical_student", "researcher", "clinician"]}}
---

# Drug Lookup

Look up detailed drug information.

## When to use

- User wants information about a specific medication
- User needs dosage, indications, or contraindications
- User is checking drug interactions

## Workflow

1. Use `med_drug_lookup` to search for drug information
2. Extract: Generic name, Brand names, Class
3. Extract: Indications, Dosage, Administration
4. Extract: Side effects, Warnings, Interactions

## Output format

```md
# Drug Information: [DRUG NAME]

## Basic Info
- **Generic Name**: [Name]
- **Brand Names**: [Names]
- **Drug Class**: [Class]

## Indications
- [Indication 1]
- [Indication 2]

## Dosage
[Adult dosage information]

## Side Effects
### Common
- [Effect 1]
- [Effect 2]

### Serious
- [Effect 1]

## Warnings
- [Warning 1]

## Interactions
- [Interaction 1]
```

## Style rules

- Always include a disclaimer
- Verify information from multiple sources
- Note any Black Box warnings
- Include pregnancy category if applicable
