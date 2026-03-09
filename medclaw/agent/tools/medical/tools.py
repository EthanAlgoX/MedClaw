"""Medical tools for MedClaw."""

from __future__ import annotations

import json
from typing import Any

import httpx

from medclaw.domain.medical.services import ClinicalTrialService, DrugService, GuidelineService, LiteratureService


class PubMedSearchTool:
    """PubMed search tool."""

    name = "med_pubmed_search"
    description = "Search PubMed for medical literature articles"

    def __init__(self):
        self.service = LiteratureService()

    async def execute(self, query: str, max_results: int = 10, **kwargs) -> dict[str, Any]:
        """Execute PubMed search."""
        try:
            articles = await self.service.search(query, max_results)
            return {
                "status": "success",
                "query": query,
                "count": len(articles),
                "articles": articles,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for PubMed",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        }


class ClinicalTrialsTool:
    """Clinical trials search tool."""

    name = "med_clinical_trials"
    description = "Search ClinicalTrials.gov for clinical trials"

    def __init__(self):
        self.service = ClinicalTrialService()

    async def execute(self, query: str, max_results: int = 10, **kwargs) -> dict[str, Any]:
        """Execute clinical trials search."""
        try:
            trials = await self.service.search(query, max_results)
            return {
                "status": "success",
                "query": query,
                "count": len(trials),
                "trials": trials,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for clinical trials",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        }


class DrugLookupTool:
    """Drug lookup tool."""

    name = "med_drug_lookup"
    description = "Look up drug information including indications, dosage, and side effects"

    def __init__(self):
        self.service = DrugService()

    async def execute(self, drug_name: str, **kwargs) -> dict[str, Any]:
        """Execute drug lookup."""
        try:
            result = await self.service.search(drug_name)
            return {
                "status": "success",
                "drug": drug_name,
                "data": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_name": {
                        "type": "string",
                        "description": "Name of the drug to look up",
                    },
                },
                "required": ["drug_name"],
            },
        }


class DrugInteractionTool:
    """Drug interaction checker tool."""

    name = "med_drug_interaction"
    description = "Check drug-drug interactions"

    def __init__(self):
        self.service = DrugService()

    async def execute(self, drug1: str, drug2: str, **kwargs) -> dict[str, Any]:
        """Check drug interactions."""
        try:
            result = await self.service.check_interaction(drug1, drug2)
            return {
                "status": "success",
                "drug1": drug1,
                "drug2": drug2,
                "interaction": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "drug1": {
                        "type": "string",
                        "description": "First drug name",
                    },
                    "drug2": {
                        "type": "string",
                        "description": "Second drug name",
                    },
                },
                "required": ["drug1", "drug2"],
            },
        }


class GuidelinesTool:
    """Clinical guidelines search tool."""

    name = "med_guidelines"
    description = "Search clinical practice guidelines"

    def __init__(self):
        self.service = GuidelineService()

    async def execute(self, condition: str, max_results: int = 10, **kwargs) -> dict[str, Any]:
        """Search clinical guidelines."""
        try:
            guidelines = await self.service.search(condition, max_results)
            return {
                "status": "success",
                "condition": condition,
                "count": len(guidelines),
                "guidelines": guidelines,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "condition": {
                        "type": "string",
                        "description": "Medical condition to search guidelines for",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                    },
                },
                "required": ["condition"],
            },
        }


def get_all_tools() -> list[dict[str, Any]]:
    """Get all available medical tools."""
    tools = [
        PubMedSearchTool(),
        ClinicalTrialsTool(),
        DrugLookupTool(),
        DrugInteractionTool(),
        GuidelinesTool(),
    ]
    return [tool.get_schema() for tool in tools]


async def execute_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a medical tool by name."""
    tools = {
        "med_pubmed_search": PubMedSearchTool(),
        "med_clinical_trials": ClinicalTrialsTool(),
        "med_drug_lookup": DrugLookupTool(),
        "med_drug_interaction": DrugInteractionTool(),
        "med_guidelines": GuidelinesTool(),
    }

    tool = tools.get(tool_name)
    if not tool:
        return {"status": "error", "error": f"Unknown tool: {tool_name}"}

    return await tool.execute(**arguments)
