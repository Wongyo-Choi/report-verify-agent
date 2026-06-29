"""검증형 시험데이터 리포트 에이전트 — Streamlit UI.

분석가 → 작성자 → 검증자 파이프라인을 실행하고, 마지막에 사람이 승인(검문소)한다.
하네스: RULES.md(작업 수칙) · 가드레일 · 보고서 양식 · 분업 노드 · 사람 승인.

공급자(Anthropic/OpenAI/Gemini 등)와 API 키는 접속자가 직접 고르고 입력한다.
키는 서버에 저장되지 않으며, 입력한 키로만 호출된다 → 과금은 접속자 본인 부담.
"""
from pathlib import Path

import litellm
import pandas as pd
import streamlit as st

from agent.config import PROVIDERS, build_model_string, load_rules, load_template
from agent.graph import stream_pipeline

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="검증형 리포트 에이전트", page_icon="🔬", layout="wide")
st.title("🔬 검증형 시험데이터 리포트 에이전트")
st.caption(
    "분석 → 보고서 작성 → 독립 검증 → 사람 승인. "
    "하네스 엔지니어링(가드레일·분업·검문소)을 LangGraph + 멀티 LLM으로 구현."
)

# --- 사이드바: 공급자/모델/키 + 하네스 자산 -----------------------------------
with st.sidebar:
    st.subheader("🤖 LLM 공급자 선택")
    provider = st.selectbox("공급자", list(PROVIDERS.keys()))
    cfg = PROVIDERS[provider]
    model_name = st.selectbox("모델", cfg["models"], index=0)
    model_name = st.text_input("모델명 직접 입력(선택)", value=model_name,
                               help="본인 키가 지원하는 다른 모델명을 직접 입력해도 됩니다.")

    st.subheader("🔑 본인 API 키")
    st.caption("키는 저장되지 않으며, 입력한 키로만 호출됩니다. (과금은 본인 키 기준)")
    api_key = st.text_input("API Key", type="password", placeholder=cfg["key_hint"],
                            label_visibility="collapsed")
    st.markdown(f"[{provider} 키 발급받기 →]({cfg['key_url']})")

    st.divider()
    st.subheader("⚙️ 하네스 설정")
    with st.expander("작업 수칙 (RULES.md)"):
        st.code(load_rules(), language="markdown")
    with st.expander("보고서 양식 (Skill)"):
        st.code(load_template(), language="markdown")

model_string = build_model_string(provider, model_name)

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
        st.error("먼저 사이드바에서 공급자를 고르고 본인 API 키를 입력하세요.")
        st.stop()

    state = {}
    progress = st.container()
    try:
        with st.status(f"파이프라인 실행 중... ({model_string})", expanded=True) as status:
            for node, partial in stream_pipeline(model_string, api_key.strip(), csv_text, memo_text):
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
    except litellm.exceptions.AuthenticationError:
        st.error("API 키 인증 실패 — 선택한 공급자에 맞는 올바른 키인지 확인하세요.")
        st.stop()
    except litellm.exceptions.RateLimitError:
        st.error("요청이 한도를 초과했습니다(본인 키 기준). 잠시 후 다시 시도하세요.")
        st.stop()
    except litellm.exceptions.NotFoundError:
        st.error(f"모델을 찾을 수 없습니다: `{model_string}`. 본인 키가 지원하는 모델명인지 확인하세요.")
        st.stop()
    except Exception as e:  # noqa: BLE001
        st.error(f"호출 오류: {e}")
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
