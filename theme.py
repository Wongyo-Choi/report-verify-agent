"""J.A.R.V.I.S. 스타일 UI — 다크 HUD 테마, 아크 원자로 애니메이션, 부팅 로딩 화면.

Streamlit은 JS를 막으므로 모든 효과는 순수 CSS 애니메이션으로 구현한다.
st.markdown(..., unsafe_allow_html=True) 로 주입.
"""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600&display=swap');

:root{ --cyan:#00d9ff; --cyan-soft:#6fe0ff; --gold:#ffb43f; }

.stApp{
  background:
    radial-gradient(1200px 620px at 50% -12%, rgba(0,170,255,.14), transparent 60%),
    radial-gradient(900px 560px at 100% 110%, rgba(255,170,40,.06), transparent 60%),
    #070b12;
  color:#cfe9ff;
  font-family:'Rajdhani',sans-serif;
}
/* 미세한 HUD 격자 */
.stApp:before{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:
    linear-gradient(rgba(0,200,255,.045) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,200,255,.045) 1px,transparent 1px);
  background-size:42px 42px;
  -webkit-mask-image:radial-gradient(circle at 50% 0%, black, transparent 80%);
  mask-image:radial-gradient(circle at 50% 0%, black, transparent 80%);
}
.block-container{ padding-top:2.2rem; position:relative; z-index:1; }

h1,h2,h3{ font-family:'Orbitron',sans-serif !important; letter-spacing:1px; }
h1{ color:#eaffff !important; text-shadow:0 0 12px rgba(0,217,255,.75),0 0 34px rgba(0,217,255,.3); }
h2,h3{ color:#bfeeff !important; text-shadow:0 0 10px rgba(0,217,255,.35); }
[data-testid="stCaptionContainer"], .stCaption{ color:#7fb8d8 !important; letter-spacing:.5px; }

/* 사이드바 — 글래스 패널 */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg, rgba(10,18,30,.96), rgba(7,11,18,.96));
  border-right:1px solid rgba(0,217,255,.28);
  box-shadow:inset -1px 0 24px rgba(0,217,255,.08);
}

/* 버튼 */
.stButton>button, .stDownloadButton>button{
  background:rgba(0,217,255,.08); color:#bdf0ff;
  border:1px solid rgba(0,217,255,.5); border-radius:10px;
  font-family:'Orbitron',sans-serif; letter-spacing:.5px; transition:all .2s ease;
}
.stButton>button:hover, .stDownloadButton>button:hover{
  border-color:var(--cyan); color:#fff; transform:translateY(-1px);
  box-shadow:0 0 18px rgba(0,217,255,.55);
}
.stButton>button[kind="primary"]{
  background:linear-gradient(90deg, rgba(0,217,255,.22), rgba(255,180,60,.18));
  border-color:var(--gold); color:#fff;
}

/* 입력 위젯 */
.stTextInput input, [data-baseweb="select"]>div, [data-baseweb="input"]{
  background:rgba(7,16,28,.85)!important; border-color:rgba(0,217,255,.3)!important;
}
[data-testid="stFileUploaderDropzone"]{
  background:rgba(7,16,28,.6); border:1px dashed rgba(0,217,255,.35);
}
[data-testid="stDataFrame"]{ border:1px solid rgba(0,217,255,.2); border-radius:8px; }
hr{ border-color:rgba(0,217,255,.2); }

/* ---------- 아크 원자로 ---------- */
.arc{ position:relative; border-radius:50%; }
.arc .core{ position:absolute; inset:33%; border-radius:50%;
  background:radial-gradient(circle, #eaffff 0%, #00d9ff 55%, #00708f 100%);
  box-shadow:0 0 16px #00d9ff, 0 0 38px rgba(0,217,255,.65);
  animation:arc-pulse 2.4s ease-in-out infinite; }
.arc .ring{ position:absolute; inset:0; border-radius:50%; border:2px solid rgba(0,217,255,.45); }
.arc .ring.r2{ inset:11%; border-style:dashed; border-color:rgba(0,217,255,.55); animation:arc-spin 7s linear infinite; }
.arc .ring.r3{ inset:21%; border-color:rgba(0,217,255,.85); animation:arc-spin 4.5s linear infinite reverse; }
.arc .seg{ position:absolute; inset:5%; border-radius:50%;
  background:conic-gradient(from 0deg,
     transparent 0 16deg, rgba(0,217,255,.30) 16deg 30deg,
     transparent 30deg 76deg, rgba(0,217,255,.30) 76deg 90deg,
     transparent 90deg 136deg, rgba(0,217,255,.30) 136deg 150deg,
     transparent 150deg 196deg, rgba(0,217,255,.30) 196deg 210deg,
     transparent 210deg 256deg, rgba(0,217,255,.30) 256deg 270deg,
     transparent 270deg 316deg, rgba(0,217,255,.30) 316deg 330deg, transparent 330deg);
  animation:arc-spin 9s linear infinite; -webkit-mask:radial-gradient(circle, transparent 52%, black 53%); mask:radial-gradient(circle, transparent 52%, black 53%); }
@keyframes arc-spin{ to{ transform:rotate(360deg);} }
@keyframes arc-pulse{ 0%,100%{ filter:brightness(1);} 50%{ filter:brightness(1.45);} }

.arc-header{ display:flex; align-items:center; gap:14px; margin:-6px 0 2px; }
.arc-header .arc{ width:64px; height:64px; flex:0 0 auto; }
.arc-header .label{ font-family:'Orbitron',sans-serif; color:var(--cyan-soft);
  letter-spacing:5px; font-size:.78rem; text-shadow:0 0 12px rgba(0,217,255,.6); }
.arc-header .label small{ display:block; color:#5f93b3; letter-spacing:2px; font-family:'Rajdhani'; }

/* ---------- 부팅 로딩 화면 ---------- */
.jarvis-boot{
  position:fixed; inset:0; z-index:99999; background:#04070d;
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:22px;
  animation:boot-fade .7s ease 2.7s forwards;
}
@keyframes boot-fade{ to{ opacity:0; visibility:hidden; } }
.jarvis-boot .arc{ width:170px; height:170px; }
.jarvis-boot .title{ font-family:'Orbitron',sans-serif; font-size:1.5rem; letter-spacing:9px;
  color:#cdf3ff; text-shadow:0 0 16px rgba(0,217,255,.8); }
.jarvis-boot .sub{ font-family:'Rajdhani',sans-serif; color:#5f9fc0; letter-spacing:3px; font-size:.85rem;
  animation:boot-flicker 1.6s steps(2) infinite; }
@keyframes boot-flicker{ 0%,100%{opacity:1;} 50%{opacity:.55;} }
.jarvis-boot .bar{ width:260px; height:3px; background:rgba(0,217,255,.15); border-radius:3px; overflow:hidden; }
.jarvis-boot .bar:before{ content:""; display:block; height:100%; width:45%;
  background:linear-gradient(90deg,transparent,#00d9ff,transparent);
  animation:boot-load 2.6s ease forwards; }
@keyframes boot-load{ from{ transform:translateX(-110%);} to{ transform:translateX(360%);} }
</style>
"""

_ARC = (
    '<div class="arc"><div class="seg"></div>'
    '<div class="ring"></div><div class="ring r2"></div><div class="ring r3"></div>'
    '<div class="core"></div></div>'
)

_BOOT = f"""
<div class="jarvis-boot">
  {_ARC}
  <div class="title">J.A.R.V.I.S.</div>
  <div class="sub">SYSTEM INITIALIZING — REPORT VERIFICATION CORE ONLINE</div>
  <div class="bar"></div>
</div>
"""

_HEADER = f"""
<div class="arc-header">
  {_ARC}
  <div class="label">J.A.R.V.I.S.
    <small>Just A Rather Very Intelligent System</small>
  </div>
</div>
"""


def inject():
    """테마 CSS 주입 — 매 실행마다 호출."""
    st.markdown(_CSS, unsafe_allow_html=True)


def boot_once():
    """첫 접속에만 부팅 로딩 화면 표시(이후 재실행에는 안 나옴)."""
    if not st.session_state.get("_booted"):
        st.markdown(_BOOT, unsafe_allow_html=True)
        st.session_state["_booted"] = True


def header():
    """타이틀 옆 아크 원자로 + JARVIS 라벨."""
    st.markdown(_HEADER, unsafe_allow_html=True)
