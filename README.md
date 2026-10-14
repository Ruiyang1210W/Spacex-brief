# Pad Brief

A 90-minute showcase agent: next SpaceX launch, ISS passes over Hawthorne, and NASA's Astronomy Picture of the Day. The model is not allowed to invent times — it has to call live tools.

## Setup

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
2. Create a venv and install:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

3. Open the local URL Streamlit prints (usually http://localhost:8501).

`NASA_API_KEY=DEMO_KEY` is enough for a short demo. Get a free key at https://api.nasa.gov/ if you hit rate limits.

## Demo script

1. Reload the dashboard — three cards should fill from live APIs (no key needed for launch/ISS).
2. Click **下一发 SpaceX 是什么？**
3. Click **今晚在 Hawthorne 能看见国际空间站吗？**
4. Click **今日 NASA 天文图拍的是什么？**

Watch the caption under the answer: it should list the tools that actually ran.
