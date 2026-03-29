from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from urllib.parse import quote
import yt_dlp
import asyncio
import os
import re
import uuid
import tempfile

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = tempfile.gettempdir()

class DownloadRequest(BaseModel):
    url: str

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    with open(os.path.join(BASE_DIR, "index.html"), "r") as f:
        return f.read()

@app.post("/download")
async def download_audio(req: DownloadRequest):
    file_id = str(uuid.uuid4())
    output_path = os.path.join(TEMP_DIR, f"{file_id}.%(ext)s")

    ydl_opts = {
        "extractor_args": {"youtube": {"player_client": ["tv_embedded"]}},
        "cookiefile": os.path.join(BASE_DIR, "cookies.txt"),
        "format": "bestaudio",
        "outtmpl": output_path,
         "concurrent_fragment_downloads": 16,
            }

    loop = asyncio.get_event_loop()

    def run_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            ext = info.get("ext", "m4a")    # ✅
            title = info.get("title", "audio")
            return title, ext               # ✅

    try:
        title, ext = await loop.run_in_executor(None, run_download)
        safe_title = re.sub(r'[^x00-\x7f]+', '_', title).strip('_') or "audio"
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

    final_path = os.path.join(TEMP_DIR, f"{file_id}.{ext}")

    if not os.path.exists(final_path):
        raise HTTPException(status_code=500, detail="File not found after download")

    with open(final_path, "rb") as f:
        audio_data = f.read()

    os.remove(final_path)

    return Response(
        content=audio_data,
        media_type=f"audio/{ext}",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.{ext}"'
        }
    )
