from pathlib import Path

from runtime.python.specialist_templates import SpecialistTemplateCatalog


def test_specialist_template_catalog_loads_real_agency_agents_repo():
    root = Path(__file__).resolve().parent.parent.parent.parent.parent / "references" / "agency-agents"
    catalog = SpecialistTemplateCatalog(str(root))

    assert catalog.summary()["count"] > 50
    assert catalog.get_template("marketing-social-media-strategist") is not None
    assert catalog.get_template("engineering-frontend-developer") is not None


def test_specialist_template_catalog_can_filter_by_division_and_query():
    root = Path(__file__).resolve().parent.parent.parent.parent.parent / "references" / "agency-agents"
    catalog = SpecialistTemplateCatalog(str(root))

    marketing = catalog.list_templates(division="marketing", limit=20)
    query_results = catalog.list_templates(query="seo", limit=20)

    assert marketing
    assert all(item["division"] == "marketing" for item in marketing)
    assert any("seo" in item["id"] for item in query_results)
