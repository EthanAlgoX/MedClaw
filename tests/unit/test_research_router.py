"""Unit tests for research workflow routing."""

from medclaw.orchestrator.router import ResearchRouter


class TestResearchRouter:
    """Tests for ResearchRouter."""

    def test_routes_trials_queries(self):
        router = ResearchRouter()
        assert router.route("Find recruiting clinical trials for EGFR lung cancer") == (
            "clinical_trial_landscape"
        )

    def test_routes_study_design_queries(self):
        router = ResearchRouter()
        assert router.route("Help with study design and sample size for a cohort") == (
            "study_design"
        )

    def test_routes_medical_queries_to_evidence_brief(self):
        router = ResearchRouter()
        assert router.route("What is known about pembrolizumab in melanoma?") == (
            "evidence_brief"
        )
