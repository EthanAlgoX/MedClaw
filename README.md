# MedClaw

<div align="center">
  <img src="medclaw_logo.png" alt="medclaw" width="420">
  <p><strong>An AI-powered medical research assistant for medical students, clinicians, and researchers.</strong></p>
</div>

## Features

- **Literature Review**: Search and summarize PubMed articles
- **Clinical Trials**: Search ClinicalTrials.gov for ongoing studies
- **Drug Information**: Look up drug indications interactions
- **Study Design**: Get guidance on clinical research, dosages, and methodology
- **Multiple Channels**: Support for Telegram, Slack, Discord, 飞书, 钉钉, Email

## Installation

```bash
git clone https://github.com/yourusername/MedClaw.git
cd MedClaw
pip install -e .
```

## Quick Start

### 1. Initialize

```bash
medclaw onboard
```

### 2. Configure

Edit `~/.medclaw/config.json` and add your API key:

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  }
}
```

### 3. Start Agent

```bash
medclaw agent
```

## Available Skills

| Skill | Description |
|-------|-------------|
| `literature-review` | Generate structured literature reviews |
| `paper-summarize` | Summarize research papers |
| `clinical-trial-search` | Search clinical trials |
| `drug-lookup` | Look up drug information |
| `study-design` | Research methodology guidance |

## Architecture

MedClaw follows a skill-first architecture:

1. **Runtime**: Message processing, session management
2. **Skills**: Task-specific capabilities (SKILL.md)
3. **Medical Domain**: Standardized data access (PubMed, ClinicalTrials, etc.)
4. **Channels**: Multi-platform message delivery

## License

MIT
