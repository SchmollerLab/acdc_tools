import time
from functools import wraps

import numpy as np

import skimage.util

from . import printl

def img_to_float(img, force_scaling=False):
    img_max = np.max(img)
    # Check if float outside of -1, 1
    if img_max <= 1:
        return img.astype(np.float64)

    uint8_max = np.iinfo(np.uint8).max
    uint16_max = np.iinfo(np.uint16).max
    if img_max <= uint8_max:
        img = img/uint8_max
    elif img_max <= uint16_max:
        img = img/uint16_max
    elif force_scaling:
        img = img/img_max
    return img

def exec_time(func):
    @wraps(func)
    def inner_function(self, *args, **kwargs):
        t0 = time.perf_counter()
        if func.__code__.co_argcount==1 and func.__defaults__ is None:
            result = func(self)
        elif func.__code__.co_argcount>1 and func.__defaults__ is None:
            result = func(self, *args)
        else:
            result = func(self, *args, **kwargs)
        t1 = time.perf_counter()
        s = f'{func.__name__} execution time = {(t1-t0)*1000:.3f} ms'
        printl(s, is_decorator=True)
        return result
    return inner_function