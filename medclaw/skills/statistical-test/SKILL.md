---
name: statistical-test
description: Help select appropriate statistical tests for research data
metadata: {"medclaw":{
  "emoji": "📊",
  "triggers": ["统计检验", "statistical test", "statistics help", "统计分析"],
  "output": "statistical-guidance",
  "risk": "low",
  "freshness": "realtime",
  "tools": [],
  "required_tools": [],
  "domains": ["clinical", "translational"],
  "user_levels": ["medical_student", "researcher"]}}
---

# Statistical Test Selection

Help select appropriate statistical tests based on study design and data.

## Decision Tree

### 1. What is your outcome variable?

- **Continuous** (e.g., blood pressure, BMI): Go to 2a
- **Categorical** (e.g., disease yes/no): Go to 2b
- **Time-to-event** (e.g., survival): Go to 2c

### 2a. Continuous Outcome

- **2 groups**: t-test (paired or unpaired)
- **>2 groups**: ANOVA
- **Repeated measures**: Repeated measures ANOVA
- **Non-normal**: Mann-Whitney, Kruskal-Wallis

### 2b. Categorical Outcome

- **2 categories**: Chi-square or Fisher's exact
- **>2 categories**: Chi-square test
- **Paired**: McNemar's test

### 2c. Time-to-Event

- **Censored data**: Kaplan-Meier, Cox regression

## Output format

```md
# Statistical Analysis Guidance

## Recommended Test
[Test Name]

## Assumptions
- [Assumption 1]
- [Assumption 2]

## Example Code (Python)
```python
import scipy.stats as stats
# Your code here
```

## Interpretation
- p < 0.05: Significant
- Effect size measures: [Cohen's d, etc.]
```
