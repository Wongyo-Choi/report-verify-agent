"""검증형 시험데이터 리포트 에이전트 — Streamlit UI.

분석가 → 작성자 → 검증자 파이프라인을 실행하고, 마지막에 사람이 승인(검문소)한다.
하네스: RULES.md(작업 수칙) · 가드레일 · 보고서 양식 · 분업 노드 · 사람 승인.

API 키는 서버에 저장하지 않고, 접속자가 직접 입력한 키로만 호출한다.
→ 다른 사람이 이 URL을 써도 과금은 그 사람 본인 키로 청구됨.
"""
import os
from pathlib import Path

import anthropic
import pandas as pd
import streamlit as st

from agent.config import MODEL, load_rules, load_template
from agent.graph import stream_pipeline

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="검증형 리포트 에이전트", page_icon="🔬", layout="wide")
st.title("🔬 검증형 시험데이터 리포트 에이전트")
st.caption(
    "분석 → 보고서 작성 → 독립 검증 → 사람 승인. "
    "하네스 엔지니어링(가드레일·분업·검문소)을 LangGraph + Claude로 구현."
)

# --- 사이드바: API 키 입력 + 하네스 자산 보기 ---------------------------------
with st.sidebar:
    st.subheader("🔑 본인 Anthropic API 키")
    st.caption("키는 서버에 저장되지 않으며, 입력한 키로만 호출됩니다. (과금은 본인 키 기준)")
    api_key = st.text_input(
        "API Key",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),  # 로컬 소유자 테스트용 자동입력
        placeholder="sk-ant-...",
        label_visibility="collapsed",
    )
    st.markdown("[키 발급받기 →](https://console.anthropic.com/settings/keys)")

    st.divider()
    st.subheader("⚙️ 하네스 설정")
    st.markdown(f"**모델**: `{MODEL}`")
    with st.expander("작업 수칙 (RULES.md)"):
        st.code(load_rules(), language="markdown")
    with st.expander("보고서 양식 (Skill)"):
        st.code(load_template(), language="markdown")

# --- 입력 ------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    csv_file = st.file_uploader("측정값 CSV", type=["csv"])
with col2:
    memo_file = st.file_uploader("현장 메모 (선택)", type=["txt"])

use_sample = st.button("📂 샘플 데이터로 실행", use_container_width=True)
run = st.button("🚀 파이프라인 실행", type="primary", use_container_width=True)

csv_text, memo_text = None, None
if use_sample:
    csv_text = (ROOT / "sample_data" / "측정값_샘플.csv").read_text(encoding="utf-8")
    memo_text = (ROOT / "sample_data" / "시험메모_샘플.txt").read_text(encoding="utf-8")
    run = True
elif run:
    if not csv_file:
        st.warning("측정값 CSV를 올리거나 '샘플 데이터로 실행'을 누르세요.")
        st.stop()
    csv_text = csv_file.getvalue().decode("utf-8")
    memo_text = memo_file.getvalue().decode("utf-8") if memo_file else None

# --- 실행 ------------------------------------------------------------------
if run and csv_text:
    if not api_key.strip():
        st.error("먼저 사이드바에 본인 Anthropic API 키를 입력하세요.")
        st.stop()

    state = {}
    progress = st.container()
    try:
        with st.status("파이프라인 실행 중...", expanded=True) as status:
            for node, partial in stream_pipeline(api_key.strip(), csv_text, memo_text):
                state.update(partial)

                if node == "guardrail":
                    if partial.get("guardrail_ok"):
                        progress.success(f"🛡️ 가드레일 통과 — {partial['guardrail_msg']}")
                    else:
                        progress.error(f"🛡️ 가드레일 차단 — {partial['guardrail_msg']}")
                        status.update(label="가드레일에서 차단됨", state="error")
                        st.stop()

                elif node == "analyst":
                    progress.info("🔎 분석가 — 측정값·기준·판정 정리 완료")
                    progress.dataframe(
                        pd.DataFrame(partial["analysis"]["items"]), use_container_width=True
                    )

                elif node == "writer":
                    progress.info("✍️ 작성자 — 보고서 초안 작성")

                elif node == "verifier":
                    v = partial["verdict"]
                    if v["passed"]:
                        progress.success(f"✅ 검증자 PASS — {v['summary']}")
                    else:
                        progress.warning(f"⚠️ 검증자 FAIL — {v['summary']}")
                        for f in v["findings"]:
                            progress.write(f"- **{f['항목']}** ({f['심각도']}): {f['문제']}")
            status.update(label="파이프라인 완료", state="complete")
        st.session_state["state"] = state
    except anthropic.AuthenticationError:
        st.error("API 키가 올바르지 않습니다. 사이드바에서 키를 다시 확인하세요.")
        st.stop()
    except anthropic.RateLimitError:
        st.error("요청이 한도를 초과했습니다(본인 키 기준). 잠시 후 다시 시도하세요.")
        st.stop()
    except anthropic.APIStatusError as e:
        st.error(f"API 오류({e.status_code}): {e.message}")
        st.stop()

# --- 결과 + 사람 승인(검문소) ----------------------------------------------
state = st.session_state.get("state")
if state and state.get("draft"):
    st.divider()
    st.subheader("📄 보고서 초안")
    st.markdown(state["draft"])

    v = state.get("verdict", {})
    st.divider()
    st.subheader("🧐 최종 승인 (사람 검문소)")
    if v.get("passed"):
        st.success("검증자가 PASS 판정함. 핵심 수치를 원본과 대조한 뒤 승인하세요.")
    else:
        st.warning("검증자가 FAIL 또는 미해결 항목을 보고함. 내용을 확인한 뒤 판단하세요.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✔️ 승인하고 보고서 확정", type="primary", use_container_width=True):
            st.session_state["approved"] = True
    with c2:
        st.download_button(
            "⬇️ 보고서 .md 내려받기",
            data=state["draft"],
            file_name="시험결과보고서_초안.md",
            mime="text/markdown",
            use_container_width=True,
        )

    if st.session_state.get("approved"):
        st.success("✅ 사람이 최종 승인함. (실제 업무에서는 이 단계가 PR 병합 = 검문소에 해당)")
