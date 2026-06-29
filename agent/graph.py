"""LangGraph 파이프라인 정의.

START → guardrail ─(ok)→ analyst → writer → verifier ─(pass/한도)→ END
                  └(차단)→ END                         └(fail)→ writer (재작성)

사람 승인(검문소)은 그래프 밖 Streamlit UI에서 처리한다.
"""
from typing import Any, Dict, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .nodes import (
    after_guardrail,
    after_verifier,
    analyst_node,
    guardrail_node,
    verifier_node,
    writer_node,
)


class PipelineState(TypedDict, total=False):
    model: str  # litellm 모델 문자열 (예: anthropic/claude-opus-4-8)
    api_key: str  # 접속자가 입력한 API 키
    csv_text: str
    memo_text: Optional[str]
    guardrail_ok: bool
    guardrail_msg: str
    analysis: Dict[str, Any]
    draft: str
    verdict: Dict[str, Any]
    revision_count: int


def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("guardrail", guardrail_node)
    g.add_node("analyst", analyst_node)
    g.add_node("writer", writer_node)
    g.add_node("verifier", verifier_node)

    g.add_edge(START, "guardrail")
    g.add_conditional_edges("guardrail", after_guardrail, {"analyst": "analyst", "blocked": END})
    g.add_edge("analyst", "writer")
    g.add_edge("writer", "verifier")
    g.add_conditional_edges("verifier", after_verifier, {"revise": "writer", "done": END})
    return g.compile()


# 모듈 import 시 한 번만 컴파일
GRAPH = build_graph()


def run_pipeline(model: str, api_key: str, csv_text: str, memo_text: Optional[str] = None) -> Dict[str, Any]:
    """전체 파이프라인을 실행하고 최종 state를 반환."""
    return GRAPH.invoke(
        {
            "model": model,
            "api_key": api_key,
            "csv_text": csv_text,
            "memo_text": memo_text,
            "revision_count": 0,
        }
    )


def stream_pipeline(model: str, api_key: str, csv_text: str, memo_text: Optional[str] = None):
    """노드별 진행 상황을 순차적으로 내보내는 제너레이터 (UI 단계 표시용)."""
    init = {
        "model": model,
        "api_key": api_key,
        "csv_text": csv_text,
        "memo_text": memo_text,
        "revision_count": 0,
    }
    for chunk in GRAPH.stream(init):
        for node_name, partial in chunk.items():
            yield node_name, partial
