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

import theme
from agent.config import PROVIDERS, build_model_string, load_rules, load_template
from agent.graph import stream_pipeline

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="J.A.R.V.I.S. · 리포트 에이전트", page_icon="🛡️", layout="wide")
theme.inject()       # JARVIS 다크 HUD 테마
theme.boot_once()    # 첫 접속 부팅 로딩 화면
theme.header()       # 아크 원자로 + JARVIS 라벨

st.title("검증형 시험데이터 리포트 에이전트")
st.caption("시험·계측 데이터를 올리면 AI가 분석·보고서 작성·검증까지 해주고, 마지막엔 사람이 승인하는 도구")

with st.expander("📖 사용법 — 어떻게 쓰나요?"):
    st.markdown(
        """
**이 도구가 하는 일**
측정값 CSV(와 현장 메모)를 올리면, 여러 AI가 분석 → 보고서 초안 작성 → 오류 검증을 자동으로 수행함. 사람은 마지막에 결과만 확인하고 승인하면 됨.

**4단계로 따라하기**
1. **공급자·키 선택** — 왼쪽 사이드바에서 LLM 공급자(Claude·ChatGPT·Gemini)와 모델을 고르고 본인 API 키를 입력함.
2. **자료 업로드** — 측정값 CSV(필수)와 현장 메모 txt(선택)를 올림. 자료가 없으면 "📂 샘플 데이터로 실행" 버튼을 누름.
3. **실행** — "🚀 파이프라인 실행"을 누르면 가드레일 → 분석 → 작성 → 검증 진행 상황이 차례로 표시됨.
4. **확인·승인** — 보고서 초안과 검증 결과(PASS / FAIL)를 확인한 뒤 "✔️ 승인" 하거나 "⬇️ .md 다운로드" 함.

**CSV 형식** — 다음 열이 있어야 함: `항목, 측정값, 단위, 기준, 판정`  (예: `진동 가속도, 3.2, m/s^2, 2.5, 불합격`)

**API 키 안내** — 키는 서버에 저장되지 않고 입력한 키로만 호출됨. 따라서 요금은 본인 키로 청구됨. 공급자별 키 발급 링크는 사이드바에 있음.
"""
    )

with st.expander("🧩 기술 구현 — 안에서 무슨 일이 일어나나요?"):
    st.markdown(
        """
**핵심 개념 — 하네스 엔지니어링 (Harness Engineering)**
"AI에게 일을 잘 시키는 법"이 아니라, AI가 안전하고 일관되게 일하도록 작업장(하네스)을 설계하는 방식. 이 도구는 그 부품들을 코드로 고정해, 누가 실행해도 같은 품질의 보고서가 나오게 함.

**멀티에이전트 파이프라인 (LangGraph로 연결)**
하나의 AI가 다 하는 게 아니라, 역할이 다른 4개 단계가 순서대로 일함.

| 단계 | 역할 | 비유 |
|---|---|---|
| 🛡️ **가드레일** | 입력 CSV 검증 — 필수 열 확인, 수식 주입(CSV 인젝션) 차단. 이상하면 분석 전에 멈춤 | 출입 보안 |
| 🔎 **분석가** | 측정값·기준·판정을 정리. 자료에 없는 값은 임의로 만들지 않고 "확인 필요"로 표시 | 데이터 분석원 |
| ✍️ **작성자** | 분석 결과를 표준 양식에 맞춰 보고서 초안으로 작성 | 보고서 담당자 |
| 🧐 **검증자** | 보고서 수치를 원본과 대조해 오류·출처 없는 값을 적발하고 PASS / FAIL 보고 | 품질 검수자(QA) |

검증자가 **FAIL** 판정을 내면 작성자에게 자동으로 되돌려 다시 쓰게 함(최대 1회). 마지막 승인은 **사람의 몫** — 즉 검문소 역할.

**왜 검증자를 따로 두나?**
자기가 쓴 보고서를 자기가 검토하면 오류를 놓치기 쉬움(자기평가 편향). 작성 과정을 모르는 독립 검증자가 백지에서 원본과 대조하므로, 그럴듯하지만 틀린 값을 잡아냄.

**환각(없는 내용 지어내기) 억제**
- 작업 수칙(RULES.md)을 모든 단계 프롬프트에 주입 → "자료에 있는 값만 사용" 규칙 강제
- 분석·검증 출력을 **구조화 스키마(JSON)** 형식으로 강제해 형식 일탈을 막음

**멀티 LLM 지원**
litellm으로 추상화해 Anthropic(Claude)·OpenAI(ChatGPT)·Google(Gemini) 등 어떤 공급자 키든 동작함.

**기술 스택** — Python · LangGraph(파이프라인) · litellm(멀티 LLM) · Pydantic(구조화 출력) · Streamlit(웹 UI)
"""
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
