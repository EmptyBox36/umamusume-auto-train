from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from server.utils import load_config, save_config
from server.live_log import attach_web_log_handler, get_logs_since, get_latest_id

app = FastAPI()

attach_web_log_handler()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.get("/config")
def get_config():
  return load_config()

@app.post("/config")
def update_config(new_config: dict):
  save_config(new_config)
  return {"status": "success", "data": new_config}

PATH = "web/dist"
DATA_PATH = "scraper/data"
DATA_PATH_2 = "data"

@app.get("/")
async def root_index():
  return FileResponse(os.path.join(PATH, "index.html"), headers={
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
  })

@app.get("/scraper/data/{path:path}")
async def get_data(path: str):
  file_path = os.path.join(DATA_PATH, path)
  headers = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
  }
  if os.path.isfile(file_path):
    return FileResponse(file_path, headers=headers)

  raise HTTPException(status_code=404, detail="Not found")

@app.get("/data/{path:path}")
async def get_data_2(path: str):
  file_path = os.path.join(DATA_PATH_2, path)
  headers = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
  }
  if os.path.isfile(file_path):
    return FileResponse(file_path, headers=headers)

  raise HTTPException(status_code=404, detail="Not found")

@app.get("/{path:path}")
async def fallback(path: str):
  file_path = os.path.join(PATH, path)
  headers = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
  }

  if os.path.isfile(file_path):
    media_type = "application/javascript" if file_path.endswith((".js", ".mjs")) else None
    return FileResponse(file_path, media_type=media_type, headers=headers)

  return FileResponse(os.path.join(PATH, "index.html"), headers=headers)

@app.get("/api/logs")
def api_logs(since: int = Query(-1, description="last seen log id")):
    """
    Return log entries newer than 'since', plus the next cursor.
    """
    entries = get_logs_since(since)
    if entries:
        nxt = entries[-1]["id"]
    else:
        nxt = get_latest_id()
    return {"next": nxt, "entries": entries}