import sys
import numpy as np

from . import widgets

def imshow(*images, points_coords=None, hide_axes=True, block=True):
    app = widgets.setupApp()
    win = widgets.ImShow()
    if app is not None:
        win.app = app
    win.setupMainLayout()
    win.setupStatusBar()
    win.setupGraphicLayout(images, hide_axes=hide_axes)
    win.showImages(images)
    if points_coords is not None:
        win.drawPoints(points_coords)
    win.run(block=block)
    return win