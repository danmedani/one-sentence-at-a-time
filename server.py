import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types

ROOT = Path(__file__).parent
STORIES_DIR = ROOT / "stories"
STATIC_DIR = ROOT / "static"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY environment variable is not set.")

client = genai.Client(api_key=api_key)
app = FastAPI()

SAFE_NAME = re.compile(r"^[A-Za-z0-9 _\-]+$")


def story_path(name: str) -> Path:
    if not SAFE_NAME.match(name):
        raise HTTPException(400, "Invalid story name (use letters, numbers, spaces, _ or -).")
    return STORIES_DIR / f"{name}.txt"


def read_story(name: str) -> str:
    p = story_path(name)
    if not p.exists():
        raise HTTPException(404, "Story not found.")
    return p.read_text(encoding="utf-8")


@app.get("/api/stories")
def list_stories():
    names = sorted(p.stem for p in STORIES_DIR.glob("*.txt"))
    return {"stories": names}


class CreateStory(BaseModel):
    name: str


@app.post("/api/stories")
def create_story(body: CreateStory):
    p = story_path(body.name)
    if p.exists():
        raise HTTPException(409, "A story with that name already exists.")
    p.write_text("", encoding="utf-8")
    return {"name": body.name}


@app.get("/api/stories/{name}")
def get_story(name: str):
    return {"name": name, "text": read_story(name)}


class ReplaceStory(BaseModel):
    text: str


@app.put("/api/stories/{name}")
def replace_story(name: str, body: ReplaceStory):
    p = story_path(name)
    if not p.exists():
        raise HTTPException(404, "Story not found.")
    p.write_text(body.text, encoding="utf-8")
    return {"text": body.text}


class AppendSentence(BaseModel):
    sentence: str


@app.post("/api/stories/{name}/append")
def append_sentence(name: str, body: AppendSentence):
    p = story_path(name)
    if not p.exists():
        raise HTTPException(404, "Story not found.")
    text = p.read_text(encoding="utf-8")
    sentence = body.sentence.strip()
    if not sentence:
        raise HTTPException(400, "Empty sentence.")
    if text and not text.endswith((" ", "\n")):
        text += " "
    text += sentence
    p.write_text(text, encoding="utf-8")
    return {"text": text}


@app.post("/api/stories/{name}/paragraph")
def new_paragraph(name: str):
    p = story_path(name)
    if not p.exists():
        raise HTTPException(404, "Story not found.")
    text = p.read_text(encoding="utf-8")
    if not text.strip():
        raise HTTPException(400, "Story is empty — write a sentence first.")
    text = text.rstrip() + "\n\n"
    p.write_text(text, encoding="utf-8")
    return {"text": text}


@app.get("/api/stories/{name}/download")
def download_story(name: str):
    p = story_path(name)
    if not p.exists():
        raise HTTPException(404, "Story not found.")
    return FileResponse(p, media_type="text/plain", filename=f"{name}.txt")


SUGGEST_SCHEMA = {
    "type": "object",
    "properties": {
        "sentences": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "maxItems": 10,
        }
    },
    "required": ["sentences"],
}


class SuggestRequest(BaseModel):
    name: str
    hint: str | None = None


@app.post("/api/suggest")
def suggest(body: SuggestRequest):
    text = read_story(body.name)
    story_block = text.strip() if text.strip() else "(The story is empty — this will be the opening sentence.)"
    hint_block = (
        f"\nThe author has given a hint for the next sentence: \"{body.hint.strip()}\". "
        "Bias the suggestions toward this hint while still offering variety."
        if body.hint and body.hint.strip()
        else ""
    )
    prompt = (
        "You are helping an author write a story one sentence at a time.\n"
        "Given the story so far, propose between 5 and 10 candidate NEXT sentences.\n"
        "Each candidate must be exactly one sentence. Vary them in tone, pacing, and direction so the author has real choices.\n"
        "Do not repeat the story so far. Do not number or label the sentences.\n"
        f"{hint_block}\n\n"
        f"--- STORY SO FAR ---\n{story_block}\n--- END ---\n"
    )
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SUGGEST_SCHEMA,
            temperature=1.0,
        ),
    )
    import json
    data = json.loads(resp.text)
    sentences = [s.strip() for s in data.get("sentences", []) if s and s.strip()]
    return {"sentences": sentences}


class TweakRequest(BaseModel):
    name: str
    sentence: str
    instruction: str


@app.post("/api/tweak")
def tweak(body: TweakRequest):
    text = read_story(body.name)
    story_block = text.strip() if text.strip() else "(The story is empty — this will be the opening sentence.)"
    prompt = (
        "You are helping an author write a story one sentence at a time.\n"
        "The author was considering a candidate next sentence, and now wants to steer it in a new direction.\n"
        "Propose between 5 and 10 NEW candidate next sentences that build on the candidate but apply the author's instruction.\n"
        "Each candidate must be exactly one sentence. Vary them in tone, pacing, and direction so the author has real choices.\n"
        "Do not repeat the story so far. Do not number or label the sentences.\n\n"
        f"--- STORY SO FAR ---\n{story_block}\n--- END ---\n\n"
        f"Candidate the author had selected: {body.sentence.strip()}\n"
        f"Author's instruction for the new direction: {body.instruction.strip()}\n"
    )
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SUGGEST_SCHEMA,
            temperature=1.0,
        ),
    )
    import json
    data = json.loads(resp.text)
    sentences = [s.strip() for s in data.get("sentences", []) if s and s.strip()]
    return {"sentences": sentences}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
