import sys
from typing import Union, Iterable
import numpy as np

import matplotlib.colors
import matplotlib.pyplot as plt

from . import widgets

def matplotlib_cmap_to_lut(
        cmap: Union[Iterable, matplotlib.colors.Colormap, str], 
        n_colors: int=256
    ):
    if isinstance(cmap, str):
        cmap = plt.get_cmap(cmap)
    
    rgbs = [cmap(i) for i in np.linspace(0,1,n_colors)]
    lut = np.zeros((256, 4), dtype=np.uint8)
    for i, rgb in enumerate(rgbs):
        lut[i] = [int(c*255) for c in rgb]
    return lut


def imshow(
        *images: np.ndarray, 
        points_coords: np.ndarray=None, 
        hide_axes: bool=True, 
        lut: Union[Iterable, matplotlib.colors.Colormap, str]=None, 
        autoLevels: bool=True,
        autoLevelsOnScroll: bool=False,
        block: bool=True,
    ):
    if lut is None:
        lut = matplotlib_cmap_to_lut('viridis')

    if isinstance(lut, str):
        lut = matplotlib_cmap_to_lut(lut)

    if isinstance(lut, np.ndarray):
        luts = [lut]*len(images)
    else:
        luts = lut
    
    if luts is not None:
        for l in range(len(luts)):
            if not isinstance(luts[l], str):
                continue
            
            luts[l] = matplotlib_cmap_to_lut(luts[l])
    
    app = widgets.setupApp()
    win = widgets.ImShow()
    if app is not None:
        win.app = app
    win.setupMainLayout()
    win.setupStatusBar()
    win.setupGraphicLayout(*images, hide_axes=hide_axes)
    win.showImages(
        *images, luts=luts, autoLevels=autoLevels, 
        autoLevelsOnScroll=autoLevelsOnScroll
    )
    if points_coords is not None:
        win.drawPoints(points_coords)
    win.run(block=block)
    return win