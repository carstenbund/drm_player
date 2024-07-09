import ctypes
import os
import numpy as np

class DRMDisplay:
    def __init__(self, device="/dev/dri/card0", width=1920, height=1080):
        self.lib = ctypes.CDLL(os.path.abspath("libdrm_display.so"))

        class FramebufferInfo(ctypes.Structure):
            _fields_ = [("fb_id", ctypes.c_uint32),
                        ("handle", ctypes.c_uint32),
                        ("pitch", ctypes.c_uint32),
                        ("size", ctypes.c_uint32),
                        ("width", ctypes.c_uint32),
                        ("height", ctypes.c_uint32)]

        self.FramebufferInfo = FramebufferInfo

        self.lib.open_device.argtypes = [ctypes.c_char_p]
        self.lib.open_device.restype = ctypes.c_int

        self.lib.create_framebuffer.argtypes = [ctypes.c_int, ctypes.c_uint32, ctypes.c_uint32]
        self.lib.create_framebuffer.restype = FramebufferInfo

        self.lib.send_to_fb.argtypes = [
            ctypes.c_int, 
            ctypes.c_uint32, 
            ctypes.c_uint32, 
            ctypes.POINTER(ctypes.c_uint8), 
            ctypes.c_uint32, 
            ctypes.c_uint32, 
            ctypes.c_uint32, 
            ctypes.c_uint32,
            ctypes.c_uint32  # Adding pitch parameter
        ]
        self.lib.send_to_fb.restype = None

        self.lib.set_crtc.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
        self.lib.set_crtc.restype = ctypes.c_int

        self.lib.get_connector.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
        self.lib.get_connector.restype = ctypes.POINTER(ctypes.c_void_p)

        self.lib.get_encoder.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
        self.lib.get_encoder.restype = ctypes.POINTER(ctypes.c_void_p)

        self.lib.get_crtc.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
        self.lib.get_crtc.restype = ctypes.POINTER(ctypes.c_void_p)

        self.lib.get_resources.argtypes = [ctypes.c_int]
        self.lib.get_resources.restype = ctypes.POINTER(ctypes.c_void_p)

        self.lib.free_resources.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        self.lib.free_resources.restype = None

        self.lib.free_connector.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        self.lib.free_connector.restype = None

        self.lib.free_encoder.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        self.lib.free_encoder.restype = None

        self.lib.free_crtc.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        self.lib.free_crtc.restype = None

        self.fd = self.lib.open_device(device.encode('utf-8'))
        if self.fd < 0:
            raise RuntimeError("Failed to open device")

        self.res = self.lib.get_resources(self.fd)
        if not self.res:
            raise RuntimeError("Failed to get resources")

        self.conn = self.lib.get_connector(self.fd, self.res)
        if not self.conn:
            self.lib.free_resources(self.res)
            raise RuntimeError("No connected connector found")

        self.enc = self.lib.get_encoder(self.fd, self.conn)
        if not self.enc:
            self.lib.free_connector(self.conn)
            self.lib.free_resources(self.res)
            raise RuntimeError("Failed to get encoder")

        self.crtc = self.lib.get_crtc(self.fd, self.enc)
        if not self.crtc:
            self.lib.free_encoder(self.enc)
            self.lib.free_connector(self.conn)
            self.lib.free_resources(self.res)
            raise RuntimeError("Failed to get CRTC")

        self.fb_info = self.lib.create_framebuffer(self.fd, width, height)
        if not self.fb_info.fb_id:
            self.lib.free_crtc(self.crtc)
            self.lib.free_encoder(self.enc)
            self.lib.free_connector(self.conn)
            self.lib.free_resources(self.res)
            raise RuntimeError("Failed to create framebuffer")

        if self.lib.set_crtc(self.fd, self.crtc, self.fb_info.fb_id, self.conn) != 0:
            self.lib.free_crtc(self.crtc)
            self.lib.free_encoder(self.enc)
            self.lib.free_connector(self.conn)
            self.lib.free_resources(self.res)
            raise RuntimeError("Failed to set CRTC")

    def send_full_image(self, data):
        data_ptr = data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        self.lib.send_to_fb(self.fd, self.fb_info.handle, self.fb_info.size, data_ptr, self.fb_info.width, self.fb_info.height, 0, 0, self.fb_info.pitch)

    def send_partial_image(self, data, x, y):
        height, width, _ = data.shape
        data_ptr = data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        self.lib.send_to_fb(self.fd, self.fb_info.handle, self.fb_info.size, data_ptr, width, height, x, y, self.fb_info.pitch)

    def __del__(self):
        self.lib.free_crtc(self.crtc)
        self.lib.free_encoder(self.enc)
        self.lib.free_connector(self.conn)
        self.lib.free_resources(self.res)

