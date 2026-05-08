# One Sentence at a Time

A small local web app that helps you grow a story one sentence at a time, with Gemini suggesting candidate next sentences.

## How it works

1. Pick a story (or create a new one with **+ New story**).
2. Optionally type a hint to steer direction, then click **Suggest next sentences**.
3. Click any suggestion — it lands in the yellow **Pending** panel (which is itself directly editable) and the other suggestions clear.
4. From the pending panel you can:
   - Edit the text directly in the textarea.
   - **Commit** — appends the pending sentence to `stories/<name>.md` and clears the pending state.
   - **Tweak** — type an instruction (e.g. "make it darker", "shorter", "from her perspective") and get a fresh batch of 5–10 candidates anchored on what you'd selected.
   - **Discard** — drop the pending sentence and start over.
5. Click **¶ New paragraph** to start a paragraph break before the next committed sentence.
6. Hover any committed paragraph to reveal **Edit** and **Delete** actions for in-place fixes.
7. Click **Download** in the header to save the current story as a `.md` file.

Stories live as Markdown (`.md`) files in `stories/`. Sentences within a paragraph are joined by single spaces; paragraphs are separated by blank lines, which Markdown renders as paragraphs (so they look nice on GitHub). You can also edit the files directly on disk — the app picks up changes whenever a story is loaded.

## Requirements

- Python 3.10+
- A Gemini API key ([aistudio.google.com/apikey](https://aistudio.google.com/apikey))

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
export GEMINI_API_KEY=your-key-here
uvicorn server:app --reload --port 8000
```

Then open <http://localhost:8000>.

If you'd rather not activate the venv each time, you can call the binaries directly:

```bash
GEMINI_API_KEY=your-key-here .venv/bin/uvicorn server:app --reload --port 8000
```

## Configuration

Environment variables read at startup:

| Variable | Default | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | _(required)_ | Server refuses to start without it. |
| `GEMINI_MODEL` | `gemini-3-flash-preview` | Any Gemini model your key has access to. |

## Layout

```
server.py             FastAPI app + Gemini calls
static/index.html     Single-page UI (vanilla JS)
stories/              Your story .md files live here
requirements.txt
```
