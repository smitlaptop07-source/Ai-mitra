import os
import time
import tempfile
from pathlib import Path
from collections import defaultdict, deque

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")  # read GEMINI_API_KEY from .env next to app.py
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "video/mp4", "video/webm", "video/quicktime"}
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
app = FastAPI(title="AI Mitra API", version="1.0.0")
app.mount("/css", StaticFiles(directory=BASE_DIR / "css"), name="css")

# Lightweight per-process protection suitable for a small student demo.
_request_times = defaultdict(deque)

def get_client_ip(request: Request) -> str:
    # Do not trust arbitrary forwarded headers for security decisions.
    return request.client.host if request.client else "unknown"

def check_rate_limit(request: Request) -> None:
    now = time.time()
    queue = _request_times[get_client_ip(request)]
    while queue and now - queue[0] > 60:
        queue.popleft()
    if len(queue) >= 12:
        raise HTTPException(status_code=429, detail="खूप प्रश्न पाठवले गेले. कृपया एका मिनिटाने पुन्हा प्रयत्न करा.")
    queue.append(now)

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="AI सेवा सुरू केलेली नाही. सर्व्हरवर GEMINI_API_KEY सेट करा.")
    return genai.Client(api_key=api_key)

@app.get("/health")
def health():
    return {"status": "ok", "service": "AI Mitra"}

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/app.js")
def frontend_script():
    return FileResponse(BASE_DIR / "app.js", media_type="application/javascript")

@app.get("/{page}.html")
def html_pages(page: str):
    if page not in {"index", "ask", "topics", "how-it-works"}:
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(BASE_DIR / f"{page}.html")

@app.post("/api/ask")
def ask_question(
    request: Request,
    message: str = Form(default=""),
    attachment: UploadFile | None = File(default=None),
):
    check_rate_limit(request)
    message = message.strip()
    if len(message) > 4000:
        raise HTTPException(status_code=413, detail="प्रश्न खूप मोठा आहे. कृपया ४००० अक्षरांपेक्षा कमी लिहा.")
    if not message and not attachment:
        raise HTTPException(status_code=400, detail="कृपया प्रश्न लिहा किंवा फोटो/व्हिडिओ जोडा.")

    prompt = (
        "You are AI Mitra, a patient tutor for school and college students. "
        "Answer primarily in simple Marathi (Devanagari), unless the student clearly asks for another language. "
        "Explain step by step, define difficult words, and use examples where helpful. "
        "For maths/science, show the working and do not invent unreadable details from an attachment. "
        "If you cannot determine something from the attachment, say so honestly.\n\n"
        f"Student's question: {message or 'Please explain the attached content in simple Marathi.'}"
    )
    client = get_gemini_client()
    contents = [prompt]
    uploaded_video_name = None
    temp_path = None
    try:
        if attachment:
            content_type = (attachment.content_type or "").lower()
            if content_type not in ALLOWED_TYPES:
                raise HTTPException(status_code=415, detail="फक्त JPG, PNG, WEBP फोटो किंवा MP4, WEBM, MOV व्हिडिओ वापरा.")
            data = attachment.file.read(MAX_UPLOAD_BYTES + 1)
            if not data:
                raise HTTPException(status_code=400, detail="जोडलेली फाइल रिकामी आहे.")
            if len(data) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="फाइल १५ MB पेक्षा लहान असावी.")

            if content_type.startswith("image/"):
                contents.append(types.Part.from_bytes(data=data, mime_type=content_type))
            else:
                suffix = Path(attachment.filename or "video.mp4").suffix or ".mp4"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                    temp.write(data)
                    temp_path = temp.name
                video_file = client.files.upload(file=temp_path, config={"mime_type": content_type})
                uploaded_video_name = video_file.name
                contents.append(video_file)

        response = client.models.generate_content(model=MODEL_NAME, contents=contents)
        answer = (response.text or "").strip()
        if not answer:
            raise HTTPException(status_code=502, detail="AI कडून उत्तर मिळाले नाही. कृपया पुन्हा प्रयत्न करा.")
        return {"answer": answer}
    except HTTPException:
        raise
    except Exception as exc:
        # Keep detailed errors in server logs, never expose keys or stack traces to clients.
        print(f"Gemini request failed ({type(exc).__name__}): {exc}")
        raise HTTPException(status_code=502, detail="AI उत्तर तयार करू शकला नाही. API quota, API key किंवा इंटरनेट कनेक्शन तपासा आणि पुन्हा प्रयत्न करा.") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if uploaded_video_name:
            try:
                client.files.delete(name=uploaded_video_name)
            except Exception:
                pass
