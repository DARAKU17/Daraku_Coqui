# ChronoVoice

A production-quality, local **AI narration toolkit** built on top of **Coqui XTTS v2**. ChronoVoice clones **your own voice** from a reference audio clip and turns text into natural, human-sounding narration — with intelligently injected pauses and a phonetics dictionary for tricky names.

The architecture is backend-agnostic: the pipeline, API and CLI are identical no matter which TTS engine is used. This makes adding new engines (Chatterbox, Kokoro, Piper, StyleTTS2, ElevenLabs, OpenAI Audio) a matter of writing a single class.

---

## Features

- **Voice cloning** — clone your own voice from a short reference `.wav` clip.
- **Natural narration** — splits text into chunks and inserts natural pauses after rhetorical phrases.
- **Correct pronunciation** — looks up tricky names in a JSON dictionary before synthesis.
- **Two interfaces** — a REST API (FastAPI) and a command-line tool (Typer).
- **Modular by design** — every stage (cleaning, chunking, pauses, pronunciation, merging) is an independent, testable class.

> **Status**: Alpha. The Coqui XTTS v2 backend is implemented; additional backends are planned (see [Roadmap](#roadmap)).

---

## Architecture

ChronoVoice uses a clean, layered architecture:

```
API (FastAPI) ─┐
               ├──> TTSService ──> Processing Pipeline ──┐
CLI (Typer) ───┘        │              │                 │
                        │              ├─ TextCleaner    │
                        │              ├─ SentenceChunk  │
                        ▼              ├─ PauseInjector  │
                 Voice Manager         ├─ Pronunciation  │
                        │              └─ AudioMerger    │
                        ▼                                 │
                 BaseTTSBackend ◄─────────────────────────┘
                        │
        +------------+------+     +----------------------+
        | CoquiBackend      |     |  (future backends)   |
        +-------------------+     +----------------------+
```

### Key ideas

- **Backend abstraction** — `BaseTTSBackend` defines `load`, `unload`, `clone_voice`, `synthesize`, and capability flags. The service layer depends only on this interface.
- **Lazy loading** — heavy libraries (`torch`, `TTS`) are imported only when the backend is actually used, so the package imports instantly and fails with clear errors if a dependency is missing.
- **Single source of truth** — configuration comes from one YAML file modelled with Pydantic.
- **One service, two UIs** — both the API and CLI call the same `TTSService`, so there is no duplicated logic.

### Adding a new backend

Every engine lives in `chronovoice/backends/`. Adding one is:

1. Create `chronovoice/backends/myengine.py` with `class MyEngineBackend(BaseTTSBackend)`.
2. Implement the required methods and declare `name = "myengine"`.
3. Register it in `chronovoice/backends/__init__.py`.

No code in the service, API, or CLI needs to change.

---

## Folder Structure

```
chronovoice/
├── chronovoice/
│   ├── api/                    # FastAPI app, routes, Pydantic schemas
│   │   ├── main.py
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── cli/                    # Typer CLI
│   │   └── main.py
│   ├── core/                   # config, structured logging, exceptions
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logger.py
│   ├── backends/               # TTS engines (backend abstraction lives here)
│   │   ├── base.py             #   BaseTTSBackend interface
│   │   ├── coqui.py            #   Coqui XTTS v2 implementation
│   │   └── __init__.py         #   registry + factory
│   ├── service/                # orchestration shared by API and CLI
│   │   └── tts_service.py
│   ├── processing/             # independent text/audio pipeline steps
│   │   ├── cleaner.py          #   TextCleaner
│   │   ├── chunker.py          #   SentenceChunker
│   │   ├── pauses.py           #   PauseInjector
│   │   ├── pronunciation.py    #   PronunciationDictionary
│   │   └── merger.py           #   AudioMerger
│   ├── voices/                 # voice library
│   │   ├── manager.py          #   VoiceManager
│   │   └── models.py           #   VoiceMetadata (Pydantic)
│   ├── service/                # synthesis orchestration
│   │   └── tts_service.py
│   └── utils/                  # shared helpers
│       └── audio.py
├── voices/                     # registered voices (one folder per voice)
│   └── daraku/
│       ├── reference.wav
│       └── metadata.json
├── data/                       # auxiliary data (pronunciation dictionary)
│   └── pronunciations.json
├── examples/                   # usage examples
├── tests/                      # pytest suite
├── config.yaml                 # default configuration
├── pyproject.toml              # project metadata + packaging
├── LICENSE                     # MIT
└── README.md
```

> **Note**: `voices/daraku/reference.wav` ships as a silent placeholder. Replace it with your own clip for real cloning (see [Add your voice](#add-your-voice)).

---

## Requirements

- Python **3.12+**
- The Coqui XTTS backend needs a few GB of RAM/VRAM. A CUDA GPU is recommended for fast synthesis but a CPU-only machine works too.

---

## Installation

Clone the repository and enter the directory:

```bash
git clone <your-repo-url> chronovoice
cd chronovoice
```

Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
```

Install the base package (tooling, config, CLI, audio pipeline):

```bash
pip install -e .
```

Install the Coqui XTTS backend (heavy — pulls `torch` and the `TTS` package):

```bash
pip install -e ".[xtts]"
```

**System dependency**: audio conversion (MP3 → WAV) uses pydub, which shells
out to the `ffmpeg` binary. Install it with your package manager:

```bash
sudo apt install ffmpeg          # Debian / Ubuntu
brew install ffmpeg              # macOS
```

On a CUDA machine you may prefer to install PyTorch first, then the XTTS extra:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -e ".[xtts]"
```

Development extras (linting / testing):

```bash
pip install -e ".[dev]"
```

The XTTS model itself is downloaded automatically on first synthesis — nothing is pre-downloaded.

---

## Configuration

All configuration lives in `config.yaml`:

```yaml
backend:
  name: coqui              # backend identifier
  device: cpu              # or "cuda"
  model_path: null         # optional path to a local model

pipeline:
  chunk_size: 400          # max characters per chunk
  pause_length: 350        # default pause length in ms
  pronunciation_path: null # optional JSON dictionary path

language: en               # default language
voice: daraku              # default voice name
output_dir: output         # where generated audio goes
voices_dir: voices         # voice library location
sample_rate: 24000         # output sample rate
```

You can point to a different config file via the `CHRONOVOICE_CONFIG` environment variable, or pass a path to `load_settings(path)` programmatically.

---

## Add your voice

1. Record **3–30 seconds** of clean speech. Little to no background noise.
   Any common format works (`.wav`, `.mp3`, `.ogg`, ...) — ChronoVoice
   automatically decodes the clip, keeps only the **first 30 seconds**, and
   resamples it to a mono 22 050 Hz WAV for storage. The target sample rate
   can be changed with `--sample-rate`.
2. Register it with the CLI (name and clip path are positional):

```bash
chronovoice voices add myname \
  /path/to/my_long_recording.mp3 \
  --language en \
  --sample-rate 22050 \
  --description "My narration voice"
```

Or copy into an existing voice — the copy is **not** converted, so prefer the
`add` command when your source is an MP3 or longer than 30 seconds:

```bash
cp /path/to/my_clip.wav voices/daraku/reference.wav
```

3. Verify it is registered:

```bash
chronovoice voices list
```

> Cloning quality depends on your clip. Keep the pitch, energy, and calm pace of the reference consistent with the text you narrate.

---

## Generating narration

### CLI

```bash
# Synthesize with the default voice
chronovoice synth "Here's the twist. My clone voice works."

# Pick a voice and output file
chronovoice synth "Congratulations, you made it." --voice daraku --output out.wav

# Read text from a file
chronovoice synth "$(cat examples/narration.txt)"
```

---

## REST API

Start the server:

```bash
python -m uvicorn chronovoice.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Endpoints

**GET /health** — backend capability & load status

```bash
curl -X GET http://127.0.0.1:8000/health
```

**GET /voices** — list registered voices

```bash
curl -X GET http://127.0.0.1:8000/voices
```

**POST /voices/create** — register a voice

```bash
curl -X POST http://127.0.0.1:8000/voices/create \
  -H "Content-Type: application/json" \
  -d '{"voice_name":"myvoice","reference_audio":"/home/user/clip.wav","language":"en"}'
```

**POST /tts** — synthesize and return the output path (JSON)

```bash
curl -X POST http://127.0.0.1:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Here is my narration.","voice":"daraku"}'
```

**POST /tts/file** — synthesize and stream the audio file

```bash
curl -X POST http://127.0.0.1:8000/tts/file \
  -H "Content-Type: application/json" \
  -d '{"text":"Here is my narration."}' \
  --output narration.wav
```

---

## Processing Pipeline details

| Stage | Class | Purpose |
|-------|-------|---------|
| Cleaning | `TextCleaner` | collapse whitespace, tidy punctuation |
| Chunking | `SentenceChunker` | split into synthesis-sized chunks |
| Pausing | `PauseInjector` | append `<break=Xms>` after rhetorical phrases |
| Pronunciation | `PronunciationDictionary` | map written words to phonetic spellings |
| Merging | `AudioMerger` | stitch chunk audio into one file |

**Pause injection & pronunciation** are data-driven: new pause rules are
`(pattern, pause_ms)` tuples, and the pronunciation dictionary is a JSON
file. See `data/pronunciations.json` for the example and add more as you go.

---

## Development

```bash
pip install -e ".[dev]"
ruff check chronovoice tests          # lint
pytest -v                              # tests (no heavy deps required)
```

Tests exercise the processing pipeline and orchestration with fakes, so you can run them without a GPU or the `TTS` package installed.

---

## Roadmap

- [x] Coqui XTTS v2 backend
- [ ] Chatterbox backend
- [ ] Kokoro backend
- [ ] Piper backend
- [ ] StyleTTS2 backend
- [ ] ElevenLabs API backend
- [ ] OpenAI Audio backend
- [ ] Streaming audio support / SSE
- [ ] Web / GUI
- [ ] Word-level timestamps

---

## License

MIT. See [LICENSE](LICENSE).

---

## Disclaimer

This project is not affiliated with the Coqui or Kweli publications. Coqui and XTTS are trademarks of their respective owners.