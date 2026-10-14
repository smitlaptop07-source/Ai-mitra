# AI Mitra — Python + Gemini backend

AI Mitra is a small Marathi student doubt-solving website. The existing HTML/CSS frontend is served by FastAPI, and the chat uses Google's Gemini API for text questions and image/video attachments.

## What works

- Text questions answered in simple Marathi
- Image questions (JPG, PNG, WEBP, HEIC/HEIF)
- Video questions (MP4, WEBM, MOV; may take longer while Gemini processes the video)
- Basic input/file-size validation and a lightweight per-IP request limit
- Health endpoint at `/health`
- Frontend and API served by the same Python service, so no separate CORS configuration is needed

Maximum attachment size is 15 MB. This is a lightweight college demo, not a production multi-user platform. The free Gemini quota can be exhausted, and Render's free service may sleep when idle.

## Run locally

1. Install Python 3.10 or newer.
2. In this folder, create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Get a Gemini API key from Google AI Studio: https://aistudio.google.com/app/apikey
4. Set the environment variable (do not paste the key into source code):

   Windows PowerShell:
   ```powershell
   $env:GEMINI_API_KEY="your_real_key_here"
   ```

   macOS/Linux:
   ```bash
   export GEMINI_API_KEY="your_real_key_here"
   ```

5. Start the app:

   ```bash
   uvicorn app:app --reload
   ```

6. Open http://127.0.0.1:8000. API health check: http://127.0.0.1:8000/health

## Deploy on Render free tier

1. Push this folder to a GitHub repository.
2. In Render, choose **New + → Blueprint** and connect the repository. Render reads `render.yaml`.
3. In the service's **Environment** settings, add `GEMINI_API_KEY` with your key. Keep it secret; never commit it to GitHub. `GEMINI_MODEL` defaults to `gemini-2.5-flash` and is already set in `render.yaml`.
4. Deploy and open the generated `https://....onrender.com` URL.
5. Check `/health`, then submit a test question on `/ask.html`.

You can alternatively create a **Web Service** manually with:

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Environment variable: `GEMINI_API_KEY` = your Gemini API key
- Health check path: `/health`

## API

`POST /api/ask` — `multipart/form-data` fields:

- `message` (optional text, maximum 4000 characters)
- `attachment` (optional image or video; maximum 15 MB)

At least one field must contain content. Success response: `{"answer":"..."}`. Errors return an HTTP status and a Marathi `detail` message.

## Notes

- Keep the API key in Render environment variables only.
- Free-tier API models and quotas can change; if the configured model is unavailable for your key, set `GEMINI_MODEL` to a model enabled in your Google AI Studio account.
- The small in-memory rate limit resets when the server restarts and is not shared across multiple instances.
- This project does not save chat history or user uploads permanently.
