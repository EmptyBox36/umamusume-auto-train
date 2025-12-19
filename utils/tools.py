# tools
import pyautogui
import time
import core.state as state

from utils.log import info, warning, error, debug

pyautogui.useImageNotFoundException(False)

def sleep(seconds=1):
  time.sleep(seconds * state.SLEEP_TIME_MULTIPLIER)

def get_secs(seconds=1):
  return seconds * state.SLEEP_TIME_MULTIPLIER

def drag_scroll(mousePos, to):
  '''to: negative to scroll down, positive to scroll up'''
  if not state.stop_event:
    return
  if not to or not mousePos:
    error("drag_scroll correct variables not supplied.")
  pyautogui.moveTo(mousePos, duration=0.1)
  pyautogui.mouseDown()
  pyautogui.moveRel(0, to, duration=0.25)
  pyautogui.mouseUp()
  pyautogui.click()

def click(img: str = None, confidence: float = 0.8, minSearch:float = 2, click: int = 1, text: str = "", boxes = None, region=None):
  if state.stop_event.is_set():
    return False

  if boxes:
    if isinstance(boxes, list):
      if len(boxes) == 0:
        return False
      box = boxes[0]
    else :
      box = boxes

    if text:
      debug(text)
    x, y, w, h = box
    center = (x + w // 2, y + h // 2)
    pyautogui.moveTo(center[0], center[1], duration=0.225)
    pyautogui.click(clicks=click, interval=0.15)
    return True

  if img is None:
    return False

  if region:
    btn = pyautogui.locateCenterOnScreen(img, confidence=confidence, minSearchTime=minSearch, region=region)
  else:
    btn = pyautogui.locateCenterOnScreen(img, confidence=confidence, minSearchTime=minSearch)
  if btn:
    if text:
      debug(text)
    pyautogui.moveTo(btn, duration=0.225)
    pyautogui.click(clicks=click, interval=0.15)
    return True

  return False

def wait_for_image(img_path, timeout=10, confidence=0.8, region=None, interval=0.15):
    """ 
    Returns:
        (True, box) if image found
        (False, None) if timeout
    """
    start = time.time()

    while time.time() - start < get_secs(timeout):
        if region:
            box = pyautogui.locateOnScreen(img_path, confidence=confidence, region=region)
        else:
            box = pyautogui.locateOnScreen(img_path, confidence=confidence)
        if box:
            return True, box
        time.sleep(get_secs(interval))

    return False, None