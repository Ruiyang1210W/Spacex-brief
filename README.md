# Pad Brief

A live space briefing dashboard with a tool-calling AI agent. It shows the next SpaceX launch, upcoming International Space Station passes over Hawthorne, CA, and NASA's Astronomy Picture of the Day, and answers questions about them in chat.

The agent is not allowed to answer from memory. Every launch time, pass time and picture title has to come from a live API call, and the interface shows which tools ran for each answer.

## Features

- **Live dashboard**: three cards for the next SpaceX launch (with a T-minus countdown), the next naked-eye ISS pass, and today's APOD image.
- **Grounded chat agent**: an OpenAI function-calling loop that must call a tool before answering anything about launches, the ISS or APOD.
- **Tool transparency**: each answer lists the tools that were actually called.
- **Local time**: all times are converted to Pacific Time for a Los Angeles audience.
- **Bilingual**: the agent replies in the language of the question (English or Chinese).
- **Failure handling**: if a data source is down, the agent says so instead of guessing. APOD falls back to a second NASA endpoint.

## How it works

```
Streamlit UI (app.py)
   ├── dashboard cards ──────────────► tools.py ──► public space APIs
   └── chat ──► agent.py ──► OpenAI ──► tool calls ──► tools.py
```

| File | Role |
| --- | --- |
| [app.py](app.py) | Streamlit interface: dashboard cards, quick-prompt buttons, chat |
| [agent.py](agent.py) | System prompt, tool schemas, and the tool-calling loop (up to 4 rounds) |
| [tools.py](tools.py) | The three data tools and their API calls |
| [.streamlit/config.toml](.streamlit/config.toml) | Dark theme |

### Tools and data sources

| Tool | Returns | Source |
| --- | --- | --- |
| `get_next_spacex_launches` | Mission, time, rocket, pad, status | [Launch Library 2](https://thespacedevs.com/llapi) (The Space Devs) |
| `get_iss_passes` | Current ISS position and visible passes for a location | [Pollux Labs ISS API](https://iss-api.polluxlabs.io/), [Open Notify](http://open-notify.org/) |
| `get_apod` | Title, explanation, image, credit | [NASA APOD API](https://api.nasa.gov/), with science.nasa.gov as fallback |

Dashboard data is cached for 3 minutes (launch, ISS) and 10 minutes (APOD).

## Getting started

### Prerequisites

- Python 3.9 or later
- An [OpenAI API key](https://platform.openai.com/api-keys) (needed for chat; the dashboard cards work without it)
- Optional: a free [NASA API key](https://api.nasa.gov/)

### Installation

```powershell
git clone https://github.com/Ruiyang1210W/Spacex-brief.git
cd Spacex-brief
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

### Configuration

Copy `.env.example` to `.env` and fill in your keys. `.env` is git-ignored; never put real keys in `.env.example`.

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | For chat | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Chat model used by the agent |
| `NASA_API_KEY` | No | `DEMO_KEY` | NASA key; `DEMO_KEY` works but has a low rate limit |
| `DEFAULT_PLACE` | No | `Hawthorne, CA` | Location name for ISS passes |
| `DEFAULT_LAT` | No | `33.9207` | Latitude for ISS passes |
| `DEFAULT_LON` | No | `-118.3280` | Longitude for ISS passes |

### Run

```powershell
streamlit run app.py
```

Then open the local URL Streamlit prints, usually http://localhost:8501.

## Usage

Use the quick-prompt buttons or type your own question:

- **Next launch**: what the next SpaceX mission is, and when and where it lifts off
- **ISS tonight**: whether the ISS is visible from Hawthorne tonight
- **Payload explained**: a one-sentence explanation of the next payload
- **Today's APOD**: what today's NASA picture shows

The caption under each answer lists the tools that ran.

## Limitations

- ISS visibility is a forecast of naked-eye passes; clouds and city lights can still hide it.
- The dashboard depends on free third-party APIs, which can rate-limit or go down.
- Times are shown in Pacific Time regardless of the location configured.
- There are no automated tests yet.

## Acknowledgements

Launch data from The Space Devs, ISS data from Pollux Labs and Open Notify, and imagery from NASA. APOD images may be copyrighted by their photographers; credit is shown where the API provides it.

This is an independent project and is not affiliated with or endorsed by SpaceX or NASA.
