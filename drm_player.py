#!/usr/bin/python3

import numpy as np
import cv2
import os
import time
import threading
from functools import wraps
from evdev import InputDevice, categorize, ecodes
from selectors import DefaultSelector, EVENT_READ
from config import ConfigLoader
from drm_display import DRMDisplay

class Canvas(object):
    def __init__(self, cf=None):
        if cf is None:
            self.config = config()
        else:
            self.config = cf
        self.screen_height = self.config.get('screen_height')
        self.screen_width = self.config.get('screen_width')
        self.canvas = np.zeros((self.screen_height, self.screen_width, 4), dtype=np.uint8)  # Change to 4 channels (RGBA)
    
    def __repr__(self):
        return repr(self.canvas)
    
    def save(self, file_name):
        cv2.imwrite(file_name, self.canvas)
    
    def clear(self):
        self.canvas[:] = 0

    def prepare_image(self, img):
        img_height, img_width = img.shape[:2]
        
        # Calculate scale to fit image to screen while maintaining aspect ratio
        scale = min(self.screen_width / img_width, self.screen_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # Calculate padding to center the image
        pad_left = (self.screen_width - new_width) // 2
        pad_top = (self.screen_height - new_height) // 2
        
        # Clear the canvas
        self.clear()
        
        # Convert the image to RGBA
        img = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)
        
        # Place the image in the center of the canvas
        self.canvas[pad_top:pad_top+new_height, pad_left:pad_left+new_width] = img

class DRMScreen(object):
    def __init__(self, device="/dev/dri/card0"):
        self.display = DRMDisplay(device)
        self.screen_width = self.display.fb_info.width
        self.screen_height = self.display.fb_info.height
        self.clear()
    
    def clear(self):
        black_canvas = np.zeros((self.screen_height, self.screen_width, 4), dtype=np.uint8)
        self.display.send_full_image(black_canvas)
    
    def show(self, canvas):
        self.display.send_full_image(canvas)

def blend_images(img1, img2, alpha):
    return cv2.addWeighted(img1, 1 - alpha, img2, alpha, 0)

def load_image(img_path, resize_dims=None):
    img = cv2.imread(img_path)
    if resize_dims:
        img = cv2.resize(img, (resize_dims), interpolation=cv2.INTER_LANCZOS4)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)  # Convert to 4 channels (BGRA)
    return np.array(img)

def get_image_paths_from_directory(directory):
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif')
    image_paths = [os.path.join(directory, filename) for filename in sorted(os.listdir(directory))
                   if filename.lower().endswith(supported_formats)]
    return image_paths

def play_images(screen, image_paths, resize=(1024,600), delay=1, blend_frames=10, stop_event=None):
    while not stop_event.is_set():
        for i in range(len(image_paths)):
            current_img = load_image(image_paths[i], resize_dims)
            next_img = load_image(image_paths[(i + 1) % len(image_paths)], resize_dims)
            for alpha in np.linspace(0, 1, blend_frames):
                start_time = time.perf_counter()
                blended_img = blend_images(current_img, next_img, alpha)
                screen.show(blended_img)
                elapsed_time = time.perf_counter() - start_time
                sleep_time = (delay / blend_frames) - elapsed_time
                if sleep_time > 0:
                    if stop_event.wait(sleep_time):
                        return
            screen.show(next_img)
            if stop_event.wait(delay):
                return

def key_listener(threads, stop_event):
    try:
        gamepad = InputDevice('/dev/input/event3')  # Change to your gamepad device
        keyboard = InputDevice('/dev/input/event4')  # Change to your keyboard device
    except:
        print("No Remote found")
        return -1

    selector = DefaultSelector()

    selector.register(gamepad, EVENT_READ)
    selector.register(keyboard, EVENT_READ)

    print('key1', gamepad)
    print('key2', keyboard)

    btn_up = ecodes.KEY_UP
    btn_down = ecodes.KEY_DOWN
    btn_pause = ecodes.KEY_PAUSE

    while True:
        for key, mask in selector.select():
            device = key.fileobj
            for event in device.read():
                if event.type == ecodes.EV_KEY and event.value == 1:
                    if event.code == btn_up:
                        print("Button up")
                        # Handle button up action
                    if event.code == btn_down:
                        print("Button down")
                        # Handle button down action
                    if event.code == btn_pause:
                        print("Button pause")
                        if stop_event.is_set():
                            stop_event.clear()
                        else:
                            stop_event.set()
        time.sleep(.5)

class KeyboardThread(threading.Thread):
    def __init__(self, threads, stop_event):
        threading.Thread.__init__(self)
        self.threads = threads
        self.stop_event = stop_event

    def run(self):
        print('run key')
        key_listener(self.threads, self.stop_event)

# usage

if __name__ == "__main__":
    config = ConfigLoader('config.ini')
    cfg = config('ImagePlayer')
    drm_screen = DRMScreen("/dev/dri/card0")
    drm_screen.clear()

    image_directory = cfg.get('image_directory')
    #images = load_from_directory(image_directory, (cfg('screen_width'), cfg('screen_height')) )
    (screen_width, screen_height) = (cfg('screen_width'), cfg('screen_height'))
    resize_dims = (screen_width, screen_height)
    image_paths = get_image_paths_from_directory(cfg('image_directory'))

    if image_paths:

        stop_event = threading.Event()

        player_thread = threading.Thread(target=play_images, args=(drm_screen, image_paths, resize_dims, cfg.get('delay'), cfg.get('blend_frames'), stop_event))
        player_thread.start()

        keyboard_thread = KeyboardThread([player_thread], stop_event)
        keyboard_thread.start()

        player_thread.join()
        keyboard_thread.join()
    else:
        print("No images found in the directory.")

