# YouTube → Interview Notes

A Streamlit app that takes a YouTube URL and generates **AI engineer interview questions and answers** from the video’s transcript using [Groq](https://groq.com/) (free LLM API).

## Setup

1. **Clone or open this project** and go to the project directory.

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Add your Groq API key**:
   - Get a free API key at [console.groq.com](https://console.groq.com/).
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and set:
     ```
     GROQ_API_KEY=your_actual_key_here
     ```
   - Optional: set `GROQ_MODEL` (default is `llama-3.3-70b-versatile`).

## Run

```bash
streamlit run app.py
```

Then open the URL shown in the terminal (usually http://localhost:8501).

## Usage

1. Paste a YouTube URL (e.g. `https://www.youtube.com/watch?v=...` or `https://youtu.be/...`).
2. Click **Generate interview Q&A**.
3. The app fetches the video transcript and sends it to Groq to generate Q&A.
4. Review the result and use **Download as .txt** to save the file.

## Notes

- The video must have **captions** (public or auto-generated). Otherwise transcript fetch will fail.
- Transcripts are truncated if very long to fit Groq’s context limit.
- Keep your `.env` file private and do not commit it (it’s in `.gitignore`).
