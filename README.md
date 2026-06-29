# 검증형 시험데이터 리포트 에이전트 (Report-Verify Agent)

시험/계측 데이터(CSV·메모)를 받아 **분석 → 보고서 작성 → 독립 검증 → 사람 승인** 파이프라인으로
정부/사내 보고서 초안을 만드는 에이전트. KIMM 고급 교육의 "하네스 엔지니어링"(분석가·작성자·검증자
분업, 가드레일, 사람 검문소)을 **LangGraph + Streamlit + Claude**로 옮긴 구현체.

## 하네스 매핑

| 고급 교육 부품 | 이 구현에서의 위치 |
|---|---|
| CLAUDE.md (작업 수칙) | `RULES.md` — 모든 노드의 system 프롬프트에 주입 |
| hooks (가드레일) | `agent/nodes.py`의 `guardrail_node` — 입력 검증·차단 |
| Skills (표준 작업서) | `report_template.md` — 보고서 양식 |
| Subagents (분석가/작성자/검증자) | LangGraph 노드 3개 (`analyst`/`writer`/`verifier`) |
| git·PR (사람 검문소) | Streamlit "승인" 단계 |

## API 키 모델 — 접속자 본인 키

이 앱은 **API 키를 서버에 저장하지 않는다.** 접속자가 사이드바에 자기 키를 직접 입력하고,
그 키로만 Claude를 호출한다. → 누가 이 URL을 써도 **과금은 그 사람 본인 키로** 청구됨.
(앱 소유자의 키가 공용으로 쓰이지 않으므로 안심하고 공개 가능)

## 빠른 시작 (로컬)

```bash
cd report-verify-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

브라우저가 열리면 사이드바에 본인 키를 입력한 뒤 `sample_data/`의 CSV·메모를 올리거나
"샘플 데이터로 실행"을 누른다. (로컬에서는 `ANTHROPIC_API_KEY` 환경변수가 있으면 자동 입력됨)

## 배포 (URL 만들기 — 과제 제출용)

1. 이 폴더를 GitHub 저장소로 push
2. https://share.streamlit.io 에서 저장소 연결 → `app.py` 지정 → Deploy
3. 발급되는 `https://<앱이름>.streamlit.app` URL을 과제 양식에 제출

> **Secrets 설정 불필요.** 키는 각 접속자가 화면에서 입력하므로 Streamlit Secrets에
> `ANTHROPIC_API_KEY`를 넣지 않는다. (넣으면 그 키가 모든 접속자에게 공용으로 과금되니 주의)
> 평가자가 키 없이 화면만 보려면, 스크린샷으로 동작 결과를 함께 제출하면 된다.

## 구조

```
report-verify-agent/
├── app.py                  # Streamlit UI + 사람 승인(검문소)
├── RULES.md                # 작업 수칙 (CLAUDE.md 역할)
├── report_template.md      # 보고서 양식 (Skill 역할)
├── agent/
│   ├── schemas.py          # 구조화 출력 스키마(Pydantic)
│   ├── config.py           # 모델·규칙 로딩
│   ├── nodes.py            # 가드레일·분석가·작성자·검증자 노드
│   └── graph.py            # LangGraph 파이프라인 정의
└── sample_data/            # 베어링 진동시험 샘플
```
