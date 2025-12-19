from core.skill import buy_skill
from utils.tools import sleep
from pathlib import Path
import pygetwindow as gw
import threading
import uvicorn
import keyboard
import pyautogui
import time
import traceback
import json

import utils.constants as constants
from utils.log import info, warning, error, debug

import core.state as state
from server.main import app
from update_config import update_config

from server.live_log import attach_web_log_handler

hotkey = "f1"

hotkey_buy_skill = "f2"
def focus_umamusume():
  try:
    win = gw.getWindowsWithTitle("Umamusume")
    target_window = next((w for w in win if w.title.strip() == "Umamusume"), None)
    if not target_window:
      if not state.WINDOW_NAME:
        error("Window name cannot be empty! Please set window name in the config.")
        return False
      info(f"Couldn't get the steam version window, trying {state.WINDOW_NAME}.")
      win = gw.getWindowsWithTitle(state.WINDOW_NAME)
      target_window = next((w for w in win if w.title.strip() == state.WINDOW_NAME), None)
      if not target_window:
        error(f"Couldn't find target window named \"{state.WINDOW_NAME}\". Please double check your window name config.")
        return False

      constants.adjust_constants_x_coords()
      if target_window.isMinimized:
        target_window.restore()
      else:
        target_window.minimize()
        sleep(0.2)
        target_window.restore()
        sleep(0.5)
      pyautogui.press("esc")
      pyautogui.press("f11")
      time.sleep(5)
      close_btn = pyautogui.locateCenterOnScreen("assets/buttons/bluestacks/close_btn.png", confidence=0.8, minSearchTime=2)
      if close_btn:
        pyautogui.click(close_btn)
      return True

    if target_window.isMinimized:
      target_window.restore()
    else:
      target_window.minimize()
      sleep(0.2)
      target_window.restore()
      sleep(0.5)
  except Exception as e:
    error(f"Error focusing window: {e}")
    return False
  return True

def main():
    print("Uma Auto!")
    try:
        state.reload_config()
        state.stop_event.clear()

        from core.EventsDatabase import load_event_databases, dump_event
        load_event_databases()

        from core.execute import career_lobby
        if focus_umamusume():
            info(f"Config: {state.CONFIG_NAME}")
            career_lobby()
        else:
            error("Failed to focus Umamusume window")
    except Exception as e:
        error_message = traceback.format_exc()
        error(f"Error in main thread: {error_message}")
    finally:
        debug("[BOT] Stopped.")


def hotkey_listener():
  while True:
    keyboard.wait(hotkey)
    with state.bot_lock:
      if state.is_bot_running:
        state.stop_bot()
        # debug("[BOT] Stopping...")
        # state.stop_event.set()
        # state.is_bot_running = False

        if state.bot_thread and state.bot_thread.is_alive():
          debug("[BOT] Waiting for bot to stop...")
          state.bot_thread.join(timeout=3)

          if state.bot_thread.is_alive():
            debug("[BOT] Bot still running, please wait...")
          else:
            debug("[BOT] Bot stopped completely")

        state.bot_thread = None
      else:
        debug("[BOT] Starting...")
        state.is_bot_running = True
        state.bot_thread = threading.Thread(target=main, daemon=True)
        state.bot_thread.start()
    sleep(0.5)

def buy_skill_hotkey_listener():
  """Listen for F2 hotkey to trigger buy_skill() directly."""
  while True:
    keyboard.wait(hotkey_buy_skill)
    try:
      from core.skill import buy_skill
      debug(f"[HOTKEY] {hotkey_buy_skill.upper()} pressed -> running buy_skill()")

      # Ensure config/state is loaded (hotkey threads start before main/reload_config)

      if not state.SKILL_LIST:
        debug("[HOTKEY] SKILL_LIST empty — reloading config before buy_skill.")
        try:
          state.reload_config()
        except Exception as e:
          error(f"Failed to reload config before buy_skill: {e}")

      # Signal other threads to stop so buy_skill runs in isolation
      try:
        state.stop_event.clear()
        # If the bot thread is running, wait briefly for it to stop
        if state.bot_thread and state.bot_thread.is_alive():
          debug("[HOTKEY] Waiting for bot thread to stop before buy_skill...")
          state.bot_thread.join(timeout=3)

        buy_skill(MIN_COST=999, MIN_DISCOUNT=10)
      finally:
        # Clear stop_event so normal processing can resume
        state.stop_event.set()
    except Exception as e:
      error(f"Error running buy_skill hotkey: {e}")
    sleep(0.5)

def start_server():
  res = pyautogui.resolution()
  if res.width != 1920 or res.height != 1080:
    error(f"Your resolution is {res.width} x {res.height}. Please set your screen to 1920 x 1080.")
    return
  host = "127.0.0.1"
  port = 8000

  cfg_path = Path("local_settings.json")
  if cfg_path.exists():
    try:
      with cfg_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
      host = data.get("host", host)
      port = int(data.get("port", port))
    except Exception as e:
      warning(f"Failed to read local_settings.json: {e}")

  info(f"Press '{hotkey}' to start/stop the bot.")
  print(f"[SERVER] Open http://{host}:{port} to configure the bot.")
  config = uvicorn.Config(app, host=host, port=port, workers=1, log_level="warning")
  server = uvicorn.Server(config)
  server.run()

if __name__ == "__main__":
  attach_web_log_handler()
  update_config()
  threading.Thread(target=hotkey_listener, daemon=True).start()
  threading.Thread(target=buy_skill_hotkey_listener, daemon=True).start()
  start_server()
