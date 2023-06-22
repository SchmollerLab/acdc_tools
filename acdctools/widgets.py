import sys
import datetime

import numpy as np
import pandas as pd

from math import ceil

from . import printl

try:
    from qtpy.QtCore import (
        QCoreApplication, QEventLoop, Qt, Signal, QTimer
    )
    from qtpy.QtWidgets import (
        QApplication, QMainWindow, QStyleFactory, QWidget, QHBoxLayout, 
        QLabel, QGraphicsProxyWidget, QScrollBar, QSpinBox
    )
except ModuleNotFoundError as e:
    print('='*50)
    print(
        '[ERROR]: The widgets module of acdctools requires the installation of qtpy. '
        'To install it, run the command `python -m pip install -U qtpy`'
    )
    print('='*50)
    exit()

try:
    import pyqtgraph as pg
    pg.setConfigOption('imageAxisOrder', 'row-major') # best performance
except ModuleNotFoundError as e:
    print('='*50)
    print(
        '[ERROR]: The widgets from acdctools requires the installation of pyqtgraph. '
        'To install it, run the command `python -m pip install -U pyqtgraph`'
    )
    print('='*50)
    exit()

def setupApp():
    app = None
    if QCoreApplication.instance() is None:
        app = QApplication(sys.argv)
        app.setStyle(QStyleFactory.create('Fusion'))
        app.setPalette(app.style().standardPalette())
    return app

class QBaseWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

    def exec_(self):
        self.show(block=True)

    def show(self, block=False):
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        super().show()
        if block:
            self.loop = QEventLoop()
            self.loop.exec_()

    def closeEvent(self, event):
        if hasattr(self, 'loop'):
            self.loop.exit()
    
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            event.ignore()
            return
            
        super().keyPressEvent(event)

class ScrollBarWithNumericControl(QWidget):
    sigValueChanged = Signal(int)
    
    def __init__(self, orientation=Qt.Horizontal, parent=None) -> None:
        super().__init__(parent)
    
        layout = QHBoxLayout()
        self.scrollbar = QScrollBar(orientation, self)
        self.spinbox = QSpinBox(self)
        self.maxLabel = QLabel(self)

        layout.addWidget(self.spinbox)
        layout.addWidget(self.maxLabel)
        layout.addWidget(self.scrollbar)

        layout.setStretch(0,0)
        layout.setStretch(1,0)
        layout.setStretch(2,1)

        self.setLayout(layout)

        self.spinbox.valueChanged.connect(self.spinboxValueChanged)
        self.scrollbar.valueChanged.connect(self.scrollbarValueChanged)
    
    def showEvent(self, event) -> None:
        super().showEvent(event)

        self.scrollbar.setMinimumHeight(self.spinbox.height())
    
    def setMaximum(self, maximum):
        self.maxLabel.setText(f'/{maximum}')
        self.scrollbar.setMaximum(maximum)
        self.spinbox.setMaximum(maximum)
    
    def spinboxValueChanged(self, value):
        self.scrollbar.setValue(value)
    
    def scrollbarValueChanged(self, value):
        self.spinbox.setValue(value)
        self.sigValueChanged.emit(value)
    
    def setValue(self, value):
        self.scrollbar.setValue(value)
    
    def value(self):
        return self.scrollbar.value()
    
    def maximum(self):
        return self.scrollbar.maximum()

class ImShowPlotItem(pg.PlotItem):
    def __init__(
            self, parent=None, name=None, labels=None, title=None, 
            viewBox=None, axisItems=None, enableMenu=True, **kargs
        ):
        super().__init__(
            parent, name, labels, title, viewBox, axisItems, enableMenu, 
            **kargs
        )
        # Overwrite zoom out button behaviour to disable autoRange after
        # clicking it.
        # If autorange is enabled, it is called everytime the brush or eraser 
        # scatter plot items touches the border causing flickering
        self.autoBtn.mode = 'manual'
        self.invertY(True)
        self.setAspectLocked(True)
        
    def autoBtnClicked(self):
        self.autoRange()
    
    def autoRange(self):
        self.vb.autoRange()
        self.autoBtn.hide()

class _ImShowImageItem(pg.ImageItem):
    sigDataHover = Signal(str)

    def __init__(self) -> None:
        super().__init__()
    
    def hoverEvent(self, event):
        if event.isExit():
            self.sigDataHover.emit('')
            return
        
        x, y = event.pos()
        xdata, ydata = int(x), int(y)
        try:
            value = self.image[ydata, xdata]
            
            self.sigDataHover.emit(
                f'x={xdata}, y={ydata}, {value = :.4f}'
            )
        except Exception as e:
            self.sigDataHover.emit('Null') 

class ImShow(QBaseWindow):
    def __init__(self, parent=None, link_scrollbars=True):
        super().__init__(parent=parent)
        self._linkedScrollbars = link_scrollbars
        self._autoLevels = True
    
    def _getGraphicsScrollbar(self, idx, image, imageItem, maximum):
        proxy = QGraphicsProxyWidget(imageItem)
        scrollbar = ScrollBarWithNumericControl(Qt.Horizontal)
        scrollbar.sigValueChanged.connect(self.OnScrollbarValueChanged)
        scrollbar.idx = idx
        scrollbar.image = image
        scrollbar.imageItem = imageItem
        scrollbar.setMaximum(maximum)
        proxy.setWidget(scrollbar)
        proxy.scrollbar = scrollbar
        return proxy
    
    def OnScrollbarValueChanged(self, value):
        scrollbar = self.sender()
        img = scrollbar.image
        imageItem = scrollbar.imageItem
        for scrollbar in imageItem.ScrollBars:
            img = img[scrollbar.value()]
        imageItem.setImage(img, autoLevels=self._autoLevels)
        self.setPointsVisible(imageItem)
        if not self._linkedScrollbars:
            return
        if len(self.ImageItems) == 1:
            return
        
        self._linkedScrollbars = False
        try:
            idx = scrollbar.idx
            for otherImageItem in self.ImageItems:
                if otherImageItem.gridPos == imageItem.gridPos:
                    continue
                if otherImageItem.image.shape != imageItem.image.shape:
                    continue
                for otherScrollbar in otherImageItem.ScrollBars:
                    if otherScrollbar.idx != idx:
                        continue
                    otherScrollbar.setValue(scrollbar.value())
        except Exception as e:
            pass
        finally:
            self._linkedScrollbars = True

    def setPointsVisible(self, imageItem):
        if not hasattr(imageItem, 'pointsItems'):
            return
        
        first_coord = imageItem.ScrollBars[0].value()
        for p, plotItem in enumerate(imageItem.pointsItems):
            if p == first_coord:
                plotItem.setVisible(True)
            else:
                plotItem.setVisible(False)
    
    def setupStatusBar(self):
        self.statusbar = self.statusBar()
        self.wcLabel = QLabel(f"")
        self.statusbar.addPermanentWidget(self.wcLabel)
    
    def setupMainLayout(self):
        self._layout = QHBoxLayout()
        self._container = QWidget()
        self._container.setLayout(self._layout)
        self.setCentralWidget(self._container)
    
    def setupGraphicLayout(
            self, *images, hide_axes=True, max_ncols=4, color_scheme='light'
        ):
        self.graphicLayout = pg.GraphicsLayoutWidget()
        self._colorScheme = color_scheme

        # Set a light background
        if color_scheme == 'light':
            self.graphicLayout.setBackground((235, 235, 235))
        else:
            self.graphicLayout.setBackground((50, 50, 50))

        ncells = max_ncols * ceil(len(images)/max_ncols)

        nrows = ncells // max_ncols
        nrows = nrows if nrows > 0 else 1
        ncols = max_ncols if len(images) > max_ncols else len(images)
        
        # Check if additional rows are needed for the scrollbars
        max_ndim = max([image.ndim for image in images])
        if max_ndim > 4:
            raise TypeError('One or more of the images have more than 4 dimensions.')
        if max_ndim == 4:
            rows_range = range(0, (nrows-1)*3+1, 3)
        elif max_ndim == 3:
            rows_range = range(0, (nrows-1)*2+1, 2)
        else:
            rows_range = range(nrows)

        self.PlotItems = []
        self.ImageItems = []
        self.ScrollBars = []
        i = 0
        for row in rows_range:
            for col in range(ncols):
                try:
                    image = images[i]
                except IndexError:
                    break
                plot = ImShowPlotItem()
                if hide_axes:
                    plot.hideAxis('bottom')
                    plot.hideAxis('left')
                self.graphicLayout.addItem(plot, row=row, col=col)
                self.PlotItems.append(plot)

                imageItem = _ImShowImageItem()
                plot.addItem(imageItem)
                self.ImageItems.append(imageItem)
                imageItem.gridPos = (row, col)
                imageItem.ScrollBars = []
                
                is_rgb = image.shape[-1] == 3
                is_rgba = image.shape[-1] == 4

                if image.ndim > 2 and not is_rgba and not is_rgb:
                    maximum = image.shape[0]-1
                    scrollbarProxy = self._getGraphicsScrollbar(
                        0, image, imageItem, maximum
                    )
                    self.graphicLayout.addItem(scrollbarProxy, row=row+1, col=col)
                    imageItem.ScrollBars.append(scrollbarProxy.scrollbar)

                if image.ndim == 4 and not is_rgba:
                    maximum = image.shape[1]-1
                    scrollbarProxy = self._getGraphicsScrollbar(
                        1, image, imageItem, maximum
                    )
                    self.graphicLayout.addItem(scrollbarProxy, row=row+1, col=col)
                    imageItem.ScrollBars.append(scrollbarProxy.scrollbar)

                i += 1
        
        self._layout.addWidget(self.graphicLayout)
    
    def setupTitles(self, *titles):
        color = 'k' if self._colorScheme == 'light' else 'w'
        for plot, title in zip(self.PlotItems, titles):
            plot.setTitle(title, color=color)
    
    def updateStatusBarLabel(self, text):
        self.wcLabel.setText(text)
    
    def autoRange(self):
        for plot in self.PlotItems:
            plot.autoRange()
    
    def showImages(
            self, *images, luts=None, autoLevels=True, 
            autoLevelsOnScroll=False
        ):
        images = [np.squeeze(img) for img in images]
        self.luts = luts
        self._autoLevels = autoLevels
        self._autoLevelsOnScroll = autoLevelsOnScroll
        for image in images:
            if image.ndim > 4 or image.ndim < 2:
                raise TypeError('Only 2-D, 3-D, and 4-D images are supported')
        
        for i, (image, imageItem) in enumerate(zip(images, self.ImageItems)):
            if luts is not None:
                imageItem.setLookupTable(luts[i])
                if not autoLevels:
                    imageItem.setLevels([0, len(luts[i])])
            else:
                self._autoLevels = True
            
            is_rgb = image.shape[-1] == 3
            is_rgba = image.shape[-1] == 4

            if image.ndim == 2 or is_rgb or is_rgba:
                imageItem.setImage(image, autoLevels=self._autoLevels)
            else:
                if not self._autoLevelsOnScroll:
                    self._autoLevels = False
                    imageItem.setLevels([image.min(), image.max()])
                for scrollbar in imageItem.ScrollBars:
                    scrollbar.setValue(int(scrollbar.maximum()/2))

            imageItem.sigDataHover.connect(self.updateStatusBarLabel)

        # Share axis between images with same X, Y shape
        all_shapes = [image.shape[-2:] for image in images]
        unique_shapes = set(all_shapes)
        shame_shape_plots = []
        for unique_shape in unique_shapes:
            plots = [
                self.PlotItems[i] for i, shape in enumerate(all_shapes) 
                if shape==unique_shape
            ]
            shame_shape_plots.append(plots)
        
        for plots in shame_shape_plots:
            for plot in plots:
                plot.vb.setYLink(plots[0].vb)
                plot.vb.setXLink(plots[0].vb)
    
    def _createPointsScatterItem(self, data=None):
        item = pg.ScatterPlotItem(
            [], [], symbol='o', pxMode=False, size=3,
            brush=pg.mkBrush(color=(255,0,0,100)),
            pen=pg.mkPen(width=2, color=(255,0,0)),
            hoverable=True, hoverBrush=pg.mkBrush((255,0,0,200)), 
            tip=None, data=data
        ) 
        return item

    def drawPoints(self, points_coords):  
        n_dim = points_coords.shape[1]
        if n_dim == 2:
            zz = [0]*len(points_coords)
            self.points_coords = np.column_stack((zz, points_coords))
            for p, plotItem in enumerate(self.PlotItems):
                imageItem = self.ImageItems[p]
                pointsItem = self._createPointsScatterItem()
                pointsItem.z = 0
                plotItem.addItem(pointsItem)
                xx = points_coords[:, 1] + 0.5
                yy = points_coords[:, 0] + 0.5   
                pointsItem.setData(xx, yy)
                imageItem.pointsItems = [pointsItem]
        elif n_dim == 3:
            self.points_coords = points_coords
            for p, plotItem in enumerate(self.PlotItems):
                imageItem = self.ImageItems[p]
                imageItem.pointsItems = []
                scrollbar = imageItem.ScrollBars[0]
                for first_coord in range(scrollbar.maximum()):
                    pointsItem = self._createPointsScatterItem()
                    pointsItem.z = first_coord
                    plotItem.addItem(pointsItem)
                    coords = points_coords[points_coords[:,0] == first_coord]
                    xx = coords[:, 2] + 0.5
                    yy = coords[:, 1] + 0.5
                    pointsItem.setData(xx, yy)
                    pointsItem.setVisible(False)
                    imageItem.pointsItems.append(pointsItem)
                self.setPointsVisible(imageItem)
    
    def setPointsData(self, points_data):
        points_df = pd.DataFrame({
            'z': self.points_coords[:, 0],
            'y': self.points_coords[:, 1],
            'x': self.points_coords[:, 2]
        })
        if isinstance(points_data, pd.Series):
            points_df[points_data.name] = points_data.values
        elif isinstance(points_data, pd.DataFrame):
            points_df = points_df.join(points_data)
        elif isinstance(points_data, np.ndarray):
            if points_data.ndim == 1:
                points_data = points_data[np.newaxis]
            else:
                points_data = points_data.T
            for i, values in enumerate(points_data):
                points_df[f'col_{i}'] = values

        self.points_df = points_df.set_index(['z', 'y', 'x']).sort_index()
        
        for p, plotItem in enumerate(self.PlotItems):
            imageItem = self.ImageItems[p]
            for pointsItem in imageItem.pointsItems:
                pointsItem.sigClicked.connect(self.pointsClicked)
        
    def pointsClicked(self, item, points, event):
        point = points[0]
        x, y = point.pos()
        coords = (item.z, int(y), int(x))
        point_data = self.points_df.loc[[coords]]
        now = datetime.datetime.now().strftime('%H:%M:%S')
        print('*'*60)
        print(f'Point clicked at {now}. Data:')
        print('-'*60)
        print(point_data)
        print('')
        print('*'*60)

    def run(self, block=False, showMaximised=False):
        if showMaximised:
            self.showMaximized()
        else:
            self.show()
        QTimer.singleShot(100, self.autoRange)
        
        if block:
            self.exec_()
    
    def resizeEvent(self, event) -> None:
        self.PlotItems[0].autoRange()       
        return super().resizeEvent(event)