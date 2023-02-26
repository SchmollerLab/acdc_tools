import sys
import numpy as np

try:
    from PyQt5.QtCore import (
        QCoreApplication, QEventLoop, Qt, pyqtSignal, QTimer
    )
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QStyleFactory, QWidget, QHBoxLayout, 
        QLabel, QGraphicsProxyWidget, QScrollBar, QSpinBox
    )
except ModuleNotFoundError as e:
    print('='*50)
    print(
        '[ERROR]: The widgets from acdctools requires the installation of PyQt5. '
        'To install it, run the command `python -m pip install -U PyQt5`'
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
    sigValueChanged = pyqtSignal(int)
    
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
    sigDataHover = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
    
    def hoverEvent(self, event):
        if event.isExit():
            self.sigDataHover.emit('')
            return
        
        x, y = event.pos()
        xdata, ydata = int(x), int(y)
        try:
            xdata, ydata = int(x), int(y)
            value = self.image[ydata, xdata]
            
            self.sigDataHover.emit(
                f'{x = :.0f}, {y = :.0f}, {value = :.4f}'
            )
        except Exception as e:
            self.sigDataHover.emit('Null') 

class ImShow(QBaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
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
    
    def setupGraphicLayout(self, *images, hide_axes=True):
        self.graphicLayout = pg.GraphicsLayoutWidget()

        # Set a light background
        self.graphicLayout.setBackground((235, 235, 235))

        nrows = len(images)//4
        nrows = nrows if nrows > 0 else 1
        ncols = 4 if len(images)>4 else len(images)
        
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
                plot = ImShowPlotItem()
                if hide_axes:
                    plot.hideAxis('bottom')
                    plot.hideAxis('left')
                self.graphicLayout.addItem(plot, row=row, col=col)
                self.PlotItems.append(plot)

                imageItem = _ImShowImageItem()
                plot.addItem(imageItem)
                self.ImageItems.append(imageItem)
                imageItem.ScrollBars = []

                image = images[i]
                if image.ndim > 2:
                    maximum = image.shape[0]-1
                    scrollbarProxy = self._getGraphicsScrollbar(0, image, imageItem, maximum)
                    self.graphicLayout.addItem(scrollbarProxy, row=row+1, col=col)
                    imageItem.ScrollBars.append(scrollbarProxy.scrollbar)

                if image.ndim == 4:
                    maximum = image.shape[1]-1
                    scrollbarProxy = self._getGraphicsScrollbar(1, image, imageItem, maximum)
                    self.graphicLayout.addItem(scrollbarProxy, row=row+1, col=col)
                    imageItem.ScrollBars.append(scrollbarProxy.scrollbar)

                i += 1
        
        self._layout.addWidget(self.graphicLayout)
    
    def updateStatusBarLabel(self, text):
        self.wcLabel.setText(text)
    
    def autoRange(self):
        for plot in self.PlotItems:
            plot.autoRange()
    
    def showImages(self, *images, luts=None, autoLevels=True):
        self.luts = luts
        self._autoLevels = autoLevels
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
                
            if image.ndim == 2:
                imageItem.setImage(image, autoLevels=self._autoLevels)
            else:
                for scrollbar in imageItem.ScrollBars:
                    scrollbar.setValue(int(scrollbar.maximum()/2))

            imageItem.sigDataHover.connect(self.updateStatusBarLabel)

        # Share axis between images with same X, Y shape
        all_shapes = [imageItem.image.shape[-2:] for imageItem in self.ImageItems]
        unique_shapes = set(all_shapes)
        shame_shape_plots = []
        for unique_shape in unique_shapes:
            plots = [self.PlotItems[i] for i, shape in enumerate(all_shapes) if shape==unique_shape]
            shame_shape_plots.append(plots)
        
        for plots in shame_shape_plots:
            for plot in plots:
                plot.vb.setYLink(plots[0].vb)
    
    def _createPointsScatterItem(self):
        item = pg.ScatterPlotItem(
            [], [], symbol='o', pxMode=False, size=3,
            brush=pg.mkBrush(color=(255,0,0,100)),
            pen=pg.mkPen(width=2, color=(255,0,0)),
            hoverable=True, hoverBrush=pg.mkBrush((255,0,0,200)), 
            tip=None
        ) 
        return item

    def drawPoints(self, points_coords):
        n_dim = points_coords.shape[1]
        if n_dim == 2:
            for plotItem in self.PlotItems:
                plotItem.pointsItem = self._createPointsScatterItem()
                plotItem.addItem(plotItem.pointsItem)
                xx = points_coords[:, 1]
                yy = points_coords[:, 0]
                plotItem.pointsItem.setData(xx, yy)
        elif n_dim == 3:
            for p, plotItem in enumerate(self.PlotItems):
                imageItem = self.ImageItems[p]
                imageItem.pointsItems = []
                scrollbar = imageItem.ScrollBars[0]
                for first_coord in range(scrollbar.maximum()):
                    pointsItem = self._createPointsScatterItem()
                    plotItem.addItem(pointsItem)
                    coords = points_coords[points_coords[:,0] == first_coord]
                    xx = coords[:, 2]
                    yy = coords[:, 1]
                    pointsItem.setData(xx, yy)
                    pointsItem.setVisible(False)
                    imageItem.pointsItems.append(pointsItem)
                self.setPointsVisible(imageItem)

    def run(self, block=False):
        self.show()
        QTimer.singleShot(100, self.autoRange)
        
        if block:
            self.exec_()