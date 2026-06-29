"""파이프라인 노드: 가드레일 → 분석가 → 작성자 → 검증자.

각 노드는 LangGraph state(dict)를 받아 갱신할 부분만 반환한다.
API 키는 환경변수가 아니라 state["api_key"](= 접속자가 UI에 입력한 키)로 전달되며,
노드마다 그 키로 일회용 클라이언트를 만들어 호출한다.
"""
import io
from typing import Any, Dict

import anthropic
import pandas as pd

from .config import MAX_REVISIONS, MODEL, load_rules, load_template
from .schemas import AnalysisResult, VerdictResult

REQUIRED_COLUMNS = ["항목", "측정값", "단위", "기준", "판정"]
# CSV 인젝션(수식 주입) 차단용 선행 문자
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _client_for(api_key: str) -> anthropic.Anthropic:
    """접속자가 입력한 키로 일회용 클라이언트 생성."""
    return anthropic.Anthropic(api_key=api_key)


def _system(role: str) -> str:
    """역할 프롬프트 + 작업 수칙(RULES.md)을 묶어 system 프롬프트로."""
    return f"{role}\n\n[반드시 지킬 작업 수칙]\n{load_rules()}"


def _parse(api_key: str, role: str, user: str, schema):
    """구조화 출력 호출 — schema(Pydantic)로 응답을 강제·검증."""
    resp = _client_for(api_key).messages.parse(
        model=MODEL,
        max_tokens=8000,
        system=_system(role),
        messages=[{"role": "user", "content": user}],
        output_format=schema,
    )
    return resp.parsed_output


def _text(api_key: str, role: str, user: str) -> str:
    """자유 형식(마크다운) 호출."""
    resp = _client_for(api_key).messages.create(
        model=MODEL,
        max_tokens=8000,
        system=_system(role),
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


# ---------------------------------------------------------------------------
# 1) 가드레일 (hooks 역할) — 위험·이상 입력을 분석 전에 차단 (API 호출 없음)
# ---------------------------------------------------------------------------
def guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    csv_text = state.get("csv_text", "") or ""
    try:
        df = pd.read_csv(io.StringIO(csv_text), dtype=str).fillna("")
    except Exception as e:  # noqa: BLE001
        return {"guardrail_ok": False, "guardrail_msg": f"CSV를 읽을 수 없음: {e}"}

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return {
            "guardrail_ok": False,
            "guardrail_msg": f"필수 열 누락: {', '.join(missing)} (필요: {', '.join(REQUIRED_COLUMNS)})",
        }

    if df.empty:
        return {"guardrail_ok": False, "guardrail_msg": "데이터 행이 없음"}

    # CSV 인젝션 차단: 셀이 수식 문자로 시작하면 거부
    for col in df.columns:
        for val in df[col]:
            if isinstance(val, str) and val.strip().startswith(_FORMULA_PREFIXES):
                return {
                    "guardrail_ok": False,
                    "guardrail_msg": f"의심스러운 수식성 값 차단: '{val}' (CSV 인젝션 방지)",
                }

    return {"guardrail_ok": True, "guardrail_msg": f"검증 통과 — {len(df)}개 항목"}


# ---------------------------------------------------------------------------
# 2) 분석가 (읽기 전용) — 측정값·기준·판정 정리, 없는 값은 "확인 필요"
# ---------------------------------------------------------------------------
def analyst_node(state: Dict[str, Any]) -> Dict[str, Any]:
    role = (
        "당신은 R&D 시험 데이터 분석 전문가다. 주어진 측정값 CSV와 현장 메모를 읽고 "
        "측정값·기준·판정을 정리해 보고한다. 자료에 있는 값만 사용하고, 없는 값은 '확인 필요'로 표시한다. "
        "원본을 수정하지 않는다."
    )
    user = (
        f"[측정값 CSV]\n{state['csv_text']}\n\n"
        f"[현장 메모]\n{state.get('memo_text') or '(없음)'}\n\n"
        "위 자료를 분석해 항목별로 정리하고, 특이사항과 후속조치를 도출하라."
    )
    result: AnalysisResult = _parse(state["api_key"], role, user, AnalysisResult)
    return {"analysis": result.model_dump()}


# ---------------------------------------------------------------------------
# 3) 작성자 — 분석 결과를 보고서 양식에 맞춰 마크다운 초안으로
# ---------------------------------------------------------------------------
def writer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    role = (
        "당신은 R&D 보고서 작성 전문가다. 전달받은 분석 결과를 보고서 양식 구조에 맞춰 "
        "마크다운 보고서 초안으로 작성한다. 문체는 '~함' 체."
    )
    feedback = state.get("verdict", {})
    feedback_text = ""
    if feedback and not feedback.get("passed", True):
        findings = "\n".join(
            f"- {f['항목']}: {f['문제']}" for f in feedback.get("findings", [])
        )
        feedback_text = (
            "\n\n[직전 검증에서 지적된 사항 — 해당 부분만 수정하고 나머지는 유지하라]\n" + findings
        )
    user = (
        f"[보고서 양식]\n{load_template()}\n\n"
        f"[분석 결과(JSON)]\n{state['analysis']}\n\n"
        "이 분석 결과로 보고서 초안을 작성하라. 양식의 4개 섹션을 모두 채워라." + feedback_text
    )
    draft = _text(state["api_key"], role, user)
    return {"draft": draft, "revision_count": state.get("revision_count", 0) + (1 if feedback_text else 0)}


# ---------------------------------------------------------------------------
# 4) 검증자 (읽기 전용) — 보고서를 원본과 대조, PASS/FAIL만 보고
# ---------------------------------------------------------------------------
def verifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
    role = (
        "당신은 품질 검증 담당자다. 작성된 보고서를 원본 데이터와 대조해 수치 오류·양식 누락·"
        "출처 없는 파생값을 점검한다. 직접 수정하지 않고 PASS/FAIL과 사유만 보고한다. "
        "확신이 없으면 보수적으로 문제를 보고하라."
    )
    user = (
        f"[원본 측정값 CSV]\n{state['csv_text']}\n\n"
        f"[현장 메모]\n{state.get('memo_text') or '(없음)'}\n\n"
        f"[검증 대상 보고서]\n{state['draft']}\n\n"
        "보고서의 모든 수치를 원본과 대조하고, 양식 섹션 누락과 작업 수칙 위반(출처 없는 % 등)을 점검하라."
    )
    result: VerdictResult = _parse(state["api_key"], role, user, VerdictResult)
    return {"verdict": result.model_dump()}


# ---------------------------------------------------------------------------
# 라우팅 함수
# ---------------------------------------------------------------------------
def after_guardrail(state: Dict[str, Any]) -> str:
    return "analyst" if state.get("guardrail_ok") else "blocked"


def after_verifier(state: Dict[str, Any]) -> str:
    if state.get("verdict", {}).get("passed"):
        return "done"
    if state.get("revision_count", 0) >= MAX_REVISIONS:
        return "done"  # 재시도 한도 도달 — 경고와 함께 종료
    return "revise"
