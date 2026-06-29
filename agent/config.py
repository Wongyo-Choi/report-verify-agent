"""모델 설정과 하네스 자산(작업 수칙·보고서 양식) 로딩."""
import os
from pathlib import Path

# Claude API 스킬 기준: 명시적 지정이 없으면 claude-opus-4-8 사용.
# 데모 비용을 줄이려면 REPORT_AGENT_MODEL=claude-sonnet-4-6 로 덮어쓸 수 있음.
MODEL = os.environ.get("REPORT_AGENT_MODEL", "claude-opus-4-8")

MAX_REVISIONS = 1  # 검증 FAIL 시 작성자에게 돌려보내는 최대 횟수

_ROOT = Path(__file__).resolve().parent.parent


def load_rules() -> str:
    """CLAUDE.md 역할 — 매 노드 system 프롬프트에 주입되는 작업 수칙."""
    return (_ROOT / "RULES.md").read_text(encoding="utf-8")


def load_template() -> str:
    """Skill 역할 — 보고서 표준 양식."""
    return (_ROOT / "report_template.md").read_text(encoding="utf-8")
