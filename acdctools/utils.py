import numpy as np

import skimage.util

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