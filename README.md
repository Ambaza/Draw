# ArtDraw Extreme — AI Prompt Drawing

This app adds an AI assistant so you can describe what to draw in plain language and have the canvas populated automatically with vector primitives.

## Setup

1) Create and/or activate your Python environment (a `.venv` is recommended).
2) Install dependencies:

```powershell
pip install -r requirements.txt
```

3) Get an OpenAI API key from https://platform.openai.com/ and keep it handy.

## Run

```powershell
python draw.py
```

- Click the left sidebar item "🤖 AI Prompt" to open the AI window.
- Paste or enter your `OPENAI_API_KEY` in the field at the top of the dialog.
- Describe your drawing and click "Generate Drawing".

The app will call OpenAI (`gpt-4o`) to produce a rich set of drawing primitives which are then rendered on the canvas and added to history for undo/redo.

## Notes

- If you prefer using an environment variable for the key, set it before launching:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

- Saving uses Pillow's `ImageGrab` on Windows. If PNG save fails, export as PostScript and convert externally.
- You can still use all existing tools (brushes, shapes, perspective, mirror) with the AI-generated content.
