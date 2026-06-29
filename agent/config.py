"""모델/공급자 설정과 하네스 자산(작업 수칙·보고서 양식) 로딩.

litellm을 통해 Anthropic·OpenAI·Gemini 등 어떤 공급자든 동일한 인터페이스로 호출한다.
"""
from pathlib import Path

MAX_REVISIONS = 1  # 검증 FAIL 시 작성자에게 돌려보내는 최대 횟수

# 공급자별 기본값. model 칸은 UI에서 자유롭게 바꿀 수 있다(본인 키가 지원하는 모델명).
PROVIDERS = {
    "Anthropic (Claude)": {
        "prefix": "anthropic/",
        "models": ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"],
        "key_hint": "sk-ant-...",
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    "OpenAI (ChatGPT)": {
        "prefix": "openai/",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
        "key_hint": "sk-...",
        "key_url": "https://platform.openai.com/api-keys",
    },
    "Google (Gemini)": {
        "prefix": "gemini/",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "key_hint": "AIza...",
        "key_url": "https://aistudio.google.com/apikey",
    },
}

_ROOT = Path(__file__).resolve().parent.parent


def build_model_string(provider: str, model_name: str) -> str:
    """litellm용 모델 문자열 생성. 이미 'provider/...' 형태면 그대로 사용."""
    model_name = (model_name or "").strip()
    if "/" in model_name:
        return model_name
    prefix = PROVIDERS.get(provider, {}).get("prefix", "")
    return f"{prefix}{model_name}"


def load_rules() -> str:
    """CLAUDE.md 역할 — 매 노드 system 프롬프트에 주입되는 작업 수칙."""
    return (_ROOT / "RULES.md").read_text(encoding="utf-8")


def load_template() -> str:
    """Skill 역할 — 보고서 표준 양식."""
    return (_ROOT / "report_template.md").read_text(encoding="utf-8")
