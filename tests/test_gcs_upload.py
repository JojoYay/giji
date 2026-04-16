"""GCS アップロードユニットテスト"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_blob_name_format():
    """blob_name が正しい形式か"""
    import uuid
    from pathlib import Path
    filename = "meeting.mp4"
    ext = Path(filename).suffix
    blob_name = f"uploads/{uuid.uuid4().hex[:12]}{ext}"
    assert blob_name.startswith("uploads/")
    assert blob_name.endswith(".mp4")
    assert len(blob_name) > 20


def test_stripe_key_no_whitespace():
    """Stripe キーに改行や空白が含まれていないことを確認"""
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).parent.parent / ".env")
    sk = os.environ.get("STRIPE_SECRET_KEY", "")
    pk = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    if sk:
        assert "\r" not in sk, f"Secret key contains \\r"
        assert "\n" not in sk, f"Secret key contains \\n"
        assert sk == sk.strip(), f"Secret key has leading/trailing whitespace"
    if pk:
        assert "\r" not in pk, f"Publishable key contains \\r"
        assert "\n" not in pk, f"Publishable key contains \\n"
        assert pk == pk.strip(), f"Publishable key has leading/trailing whitespace"


def test_meeting_context_dataclass():
    """MeetingContext が正しく初期化されるか"""
    from gemini_transcribe_v2 import MeetingContext
    ctx = MeetingContext(
        date="2024-04-14",
        time="10:00-12:00",
        topic="テスト会議",
        participants="山田, 吉田",
        keywords="KPI, RPA",
    )
    assert ctx.date == "2024-04-14"
    assert ctx.topic == "テスト会議"
    assert ctx.reference_texts == []


def test_summary_templates_exist():
    """全テンプレートが4言語分存在するか"""
    from gemini_transcribe_v2 import SUMMARY_TEMPLATES, SUPPORTED_LANGUAGES
    for tpl_key, tpl in SUMMARY_TEMPLATES.items():
        for lang_code in SUPPORTED_LANGUAGES:
            assert lang_code in tpl["name"], f"Missing name for {tpl_key}/{lang_code}"
            assert lang_code in tpl["description"], f"Missing desc for {tpl_key}/{lang_code}"
            if tpl_key != "custom":
                assert lang_code in tpl["template"], f"Missing template for {tpl_key}/{lang_code}"
                assert len(tpl["template"][lang_code]) > 50, f"Template too short: {tpl_key}/{lang_code}"


def test_get_summary_prompt_with_template():
    """テンプレート指定時にプロンプトが正しく生成されるか"""
    from gemini_transcribe_v2 import get_summary_prompt
    prompt = get_summary_prompt("ja", template_key="action_focused")
    assert "{transcript}" in prompt
    assert "アクション" in prompt


def test_get_summary_prompt_custom():
    """カスタムテンプレートが正しく適用されるか"""
    from gemini_transcribe_v2 import get_summary_prompt
    custom = "# My Template\n## Section A\n## Section B"
    prompt = get_summary_prompt("en", template_key="custom", custom_template=custom)
    assert "My Template" in prompt
    assert "{transcript}" in prompt


def test_get_transcript_prompt_with_context():
    """MeetingContext付きでプロンプトが拡張されるか"""
    from gemini_transcribe_v2 import get_transcript_prompt, MeetingContext
    ctx = MeetingContext(keywords="RPA, KPI", participants="山田, 吉田")
    prompt = get_transcript_prompt("ja", ctx)
    assert "RPA" in prompt
    assert "山田" in prompt


def test_build_context_block():
    """コンテキストブロックが正しく生成されるか"""
    from gemini_transcribe_v2 import _build_context_block, MeetingContext
    ctx = MeetingContext(
        date="2024-04-14", time="10:00", topic="Q2 Review",
        participants="Alice, Bob", glossary="KPI=Key Performance Indicator",
    )
    block = _build_context_block(ctx, "en")
    assert "2024-04-14" in block
    assert "Q2 Review" in block
    assert "Alice" in block
    assert "KPI" in block


def test_correction_prompts_exist():
    """校正プロンプトが4言語分あるか"""
    from gemini_transcribe_v2 import CORRECTION_PROMPTS, SUPPORTED_LANGUAGES
    for lang_code in SUPPORTED_LANGUAGES:
        assert lang_code in CORRECTION_PROMPTS, f"Missing correction prompt for {lang_code}"
        assert "{raw_transcript}" in CORRECTION_PROMPTS[lang_code]
        assert "{context_block}" in CORRECTION_PROMPTS[lang_code]
