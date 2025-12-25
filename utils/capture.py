import cv2
import numpy as np
import pyautogui


def screenshot_bgr(region=None):
    im = pyautogui.screenshot(region=region)  # PIL RGB
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
