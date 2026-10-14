from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st
from dotenv import load_dotenv

from agent import run_agent
from tools import DEFAULT_LAT, DEFAULT_LON, DEFAULT_PLACE, get_apod, get_iss_passes, get_next_spacex_launches

load_dotenv()

st.set_page_config(
    page_title="Pad Brief",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    .stApp { background: radial-gradient(1200px 500px at 10% -10%, #1b2744 0%, #070b14 45%, #05070d 100%); }
    h1, h2, h3, p, label { color: #e8eefc !important; }
    .brief-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        min-height: 180px;
    }
    .kicker { color: #8fb4ff; font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; }
    .muted { color: #9aa7c2 !important; font-size: 0.9rem; }
</style>
""",
    unsafe_allow_html=True,
)

QUICK = [
    "下一发 SpaceX 是什么？什么时候、从哪打？",
    "今晚在 Hawthorne 能看见国际空间站吗？",
    "这发载荷是干什么的？用一句话讲给外行听。",
    "今日 NASA 天文图拍的是什么？",
]


@st.cache_data(ttl=180)
def load_launch():
    return get_next_spacex_launches(limit=1)


@st.cache_data(ttl=180)
def load_iss():
    return get_iss_passes(lat=DEFAULT_LAT, lon=DEFAULT_LON, place=DEFAULT_PLACE, n=3)


@st.cache_data(ttl=600)
def load_apod():
    return get_apod()


def countdown(unix: int | None) -> str:
    if not unix:
        return "TBD"
    delta = unix - int(datetime.now(timezone.utc).timestamp())
    if delta <= 0:
        return "Window opened / recently launched"
    d, rem = divmod(delta, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    if d:
        return f"T-{d}d {h}h {m}m"
    return f"T-{h}h {m}m"


st.title("Pad Brief")
st.caption(
    f"Live SpaceX pad intern · default site {DEFAULT_PLACE} "
    f"({DEFAULT_LAT:.4f}, {DEFAULT_LON:.4f}) · {datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%b %d, %Y %I:%M %p PT')}"
)

launch_data = load_launch()
iss_data = load_iss()
apod_data = load_apod()

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown('<div class="brief-card">', unsafe_allow_html=True)
    st.markdown('<div class="kicker">Next SpaceX launch</div>', unsafe_allow_html=True)
    if launch_data.get("ok") and launch_data.get("launches"):
        L = launch_data["launches"][0]
        st.subheader(L.get("name") or "Upcoming mission")
        st.write(f"**{countdown((L.get('net') or {}).get('unix'))}**")
        st.markdown(
            f"<p class='muted'>{(L.get('net') or {}).get('los_angeles') or 'Time TBD'}<br>"
            f"{L.get('rocket') or ''} · {L.get('pad') or ''}<br>"
            f"Status: {L.get('status') or '—'}</p>",
            unsafe_allow_html=True,
        )
    else:
        st.write(launch_data.get("error") or "Launch data unavailable.")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="brief-card">', unsafe_allow_html=True)
    st.markdown('<div class="kicker">ISS over Hawthorne</div>', unsafe_allow_html=True)
    if iss_data.get("ok"):
        pos = iss_data.get("iss_now") or {}
        if pos:
            st.write(f"Now: {pos.get('latitude')}, {pos.get('longitude')}")
        passes = iss_data.get("visible_passes") or []
        if passes:
            first = passes[0]
            when = (first.get("visible_start") or first.get("rise") or first.get("max") or {}).get("los_angeles")
            heading = first.get("appears_from")
            elev = first.get("max_elevation_deg")
            st.subheader("Next visible pass")
            st.write(when or "See chat for details")
            extra = []
            if heading:
                extra.append(f"from the {heading}")
            if elev:
                extra.append(f"max {elev}°")
            if extra:
                st.caption(" · ".join(extra) + ". Clouds and city lights can still hide it.")
            else:
                st.caption("Naked-eye passes only. Clouds and light pollution can still hide it.")
        else:
            st.write("No strong naked-eye passes in the near forecast for this site.")
    else:
        st.write(iss_data.get("error") or "ISS data unavailable.")
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown('<div class="brief-card">', unsafe_allow_html=True)
    st.markdown('<div class="kicker">NASA APOD</div>', unsafe_allow_html=True)
    if apod_data.get("ok"):
        st.subheader(apod_data.get("title") or "Picture of the Day")
        st.caption(apod_data.get("date") or "")
        if apod_data.get("media_type") == "image" and apod_data.get("url"):
            st.image(apod_data["url"], use_container_width=True)
        elif apod_data.get("url"):
            st.write(apod_data["url"])
    else:
        st.write(apod_data.get("error") or "APOD unavailable.")
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()
st.subheader("Ask the intern")
st.caption("Answers about times and sky must come from live tools, not model memory.")

if "messages" not in st.session_state:
    st.session_state.messages = []

cols = st.columns(4)
for i, q in enumerate(QUICK):
    if cols[i].button(q, use_container_width=True):
        st.session_state.pending = q

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tools"):
            st.caption("Tools: " + ", ".join(msg["tools"]))

prompt = st.chat_input("Ask about the next launch, ISS tonight, or today's picture…")
if "pending" in st.session_state:
    prompt = st.session_state.pop("pending")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "").startswith("sk-your-key"):
            text = "还差一步：在项目里的 `.env` 填入 `OPENAI_API_KEY`，然后重新运行。"
            used = []
            st.markdown(text)
        else:
            with st.spinner("Calling live space data…"):
                try:
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                        if m["role"] in ("user", "assistant")
                    ]
                    text, used = run_agent(history)
                except Exception as exc:
                    text, used = f"Agent error: {exc}", []
            st.markdown(text)
            if used:
                st.caption("Tools: " + ", ".join(used))
    st.session_state.messages.append({"role": "assistant", "content": text, "tools": used})
