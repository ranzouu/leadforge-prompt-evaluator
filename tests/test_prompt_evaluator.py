from leadforge_prompt_evaluator.experiment import Lead, PROMPT_VARIANTS, _load_leads, _render_prompt


def test_load_leads():
    leads = _load_leads()
    assert len(leads) >= 1
    assert leads[0].id


def test_prompt_rendering():
    lead = Lead(id="L001", name="X", category="academia", city="Fortaleza")
    rendered = _render_prompt(PROMPT_VARIANTS["v2_structured"], lead)
    assert "X" in rendered
    assert "academia" in rendered
    assert "Fortaleza" in rendered
