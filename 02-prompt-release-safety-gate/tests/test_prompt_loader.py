import pytest

from app.prompts.loader import list_prompts, load_prompt


def test_list_prompts_finds_bundled_yaml_files():
    names = list_prompts()
    assert "crm_summary_v1" in names
    assert "crm_summary_v2" in names


def test_load_prompt_v1_matches_schema():
    prompt = load_prompt("crm_summary_v1")
    assert prompt.name == "crm_summary"
    assert prompt.version == "v1"
    assert prompt.owner
    assert prompt.model_settings.model == "stub"
    assert prompt.model_settings.style == "concise"
    assert len(prompt.few_shot_examples) >= 1
    assert prompt.output_schema == "NoteSummary"


def test_load_prompt_v2_is_verbose_candidate():
    prompt = load_prompt("crm_summary_v2")
    assert prompt.version == "v2"
    assert prompt.model_settings.style == "verbose"


def test_load_prompt_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt("does_not_exist")
