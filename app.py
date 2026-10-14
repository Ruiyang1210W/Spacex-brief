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
    @import url('https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600&display=swap');

    html, body, .stApp, .stApp p, .stApp label, .stApp button, .stApp textarea {
        font-family: 'Barlow', 'D-DIN', 'Helvetica Neue', Arial, sans-serif;
    }
    .stApp, [data-testid="stHeader"], [data-testid="stBottomBlockContainer"] { background: #000; }
    .block-container { padding-top: 3rem; max-width: 1280px; }

    h1, h2, h3 { color: #fff !important; text-transform: uppercase; font-weight: 600 !important; }
    h1 { letter-spacing: 0.18em; font-size: 2.4rem !important; }
    h3 { letter-spacing: 0.06em; font-size: 1.25rem !important; }
    [data-testid="stCaptionContainer"] { color: #8a8a8a !important; letter-spacing: 0.04em; }
    hr { border-color: rgba(255,255,255,0.18) !important; }

    [class*="st-key-card_"] {
        background: #000;
        border: 1px solid rgba(255,255,255,0.22);
        border-radius: 0;
        padding: 1.4rem 1.5rem;
        min-height: 260px;
    }
    .kicker { color: #fff; font-size: 0.72rem; font-weight: 500; letter-spacing: 0.22em; text-transform: uppercase; opacity: 0.7; }
    .countdown { color: #fff; font-size: 2rem; font-weight: 300; letter-spacing: 0.08em; margin: 0.2rem 0 0.6rem; }
    .muted { color: #9a9a9a !important; font-size: 0.9rem; line-height: 1.6; }

    .stButton > button {
        background: #000 !important;
        color: #fff !important;
        border: 1px solid #fff !important;
        border-radius: 0 !important;
        padding: 0.75rem 1rem;
        transition: background 0.25s ease, color 0.25s ease;
    }
    .stButton > button p {
        color: inherit !important;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }
    .stButton > button:hover, .stButton > button:focus-visible {
        background: #fff !important;
        color: #000 !important;
    }
    .stButton > button:active { background: #d0d0d0 !important; color: #000 !important; }

    [data-testid="stChatInput"] > div { background: #000; border: 1px solid rgba(255,255,255,0.45); border-radius: 0; }
    [data-testid="stChatMessage"] { background: transparent; border-bottom: 1px solid rgba(255,255,255,0.12); border-radius: 0; }
    [data-testid="stImage"] img { border-radius: 0; }
</style>
""",
    unsafe_allow_html=True,
)

# Button label -> prompt sent to the agent
QUICK = {
    "Next launch": "What is the next SpaceX launch? When and where does it lift off?",
    "ISS tonight": "Can I see the ISS from Hawthorne tonight?",
    "Payload explained": "What does the payload on the next launch do? Explain it in one sentence for a non-expert.",
    "Today's APOD": "What does today's NASA Astronomy Picture of the Day show?",
}


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

with c1, st.container(key="card_launch"):
    st.markdown('<div class="kicker">Next SpaceX launch</div>', unsafe_allow_html=True)
    if launch_data.get("ok") and launch_data.get("launches"):
        L = launch_data["launches"][0]
        st.subheader(L.get("name") or "Upcoming mission")
        st.markdown(
            f"<div class='countdown'>{countdown((L.get('net') or {}).get('unix'))}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p class='muted'>{(L.get('net') or {}).get('los_angeles') or 'Time TBD'}<br>"
            f"{L.get('rocket') or ''} · {L.get('pad') or ''}<br>"
            f"Status: {L.get('status') or '—'}</p>",
            unsafe_allow_html=True,
        )
    else:
        st.write(launch_data.get("error") or "Launch data unavailable.")

with c2, st.container(key="card_iss"):
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

with c3, st.container(key="card_apod"):
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

st.divider()
st.subheader("Ask the intern")
st.caption("Answers about times and sky must come from live tools, not model memory.")

if "messages" not in st.session_state:
    st.session_state.messages = []

cols = st.columns(len(QUICK))
for col, (label, q) in zip(cols, QUICK.items()):
    if col.button(label, use_container_width=True):
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
            text = "One more step: set `OPENAI_API_KEY` in the project's `.env`, then rerun."
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
