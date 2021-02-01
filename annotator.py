import os
import pickle
import sys
import numpy as np
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from utils import get_unique_names, get_all_paths_and_channels, get_obj_channels, validateDirectoryFormat

Image.MAX_IMAGE_PIXELS = None


class PhotoViewer(QtWidgets.QGraphicsView):
    photoClicked = QtCore.pyqtSignal(QtCore.QPoint)
    photoReleased = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        self.zoom = 0
        self._empty = True
        self.scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self.scene.addItem(self._photo)
        self.setScene(self.scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)

            # resizing...
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            # self._zoom = 0

        self.scene.addLine(QtCore.QLineF(200, 200, 200, 500))
        self.scene.update()

    def setPhoto(self, pixmap=None, channel_change=False):
        # self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            if not channel_change:
                self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
            # self._photo.
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self._photo.setPixmap(QtGui.QPixmap())
        self.fitInView()

    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                # positive zoom case
                factor = 1.25
                self.zoom += 1
            else:
                factor = 0.8
                self.zoom -= 1
            if self.zoom > 0:
                self.scale(factor, factor)
            elif self.zoom == 0:
                self.fitInView()
            elif self.zoom < 0:
                self.zoom = 0

    def toggleDragMode(self, state):
        if state:
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)

        # if self.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag:
        #     self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        # elif not self._photo.pixmap().isNull():
        #     self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        if self._photo.isUnderMouse():
            self.photoClicked.emit(self.mapToScene(event.pos()).toPoint())
        super(PhotoViewer, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._photo.isUnderMouse():
            self.photoReleased.emit(self.mapToScene(event.pos()).toPoint())
        super(PhotoViewer, self).mouseReleaseEvent(event)


class Window(QtWidgets.QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.directory = None

        self.viewer = PhotoViewer(self)
        self.viewer.photoClicked.connect(self.photoClicked)
        self.viewer.photoReleased.connect(self.photoReleased)

        # 'Load image' button
        self.btnLoad = QtWidgets.QToolButton(self)
        self.btnLoad.setText('Open Image Directory')
        self.btnLoad.clicked.connect(self.loadImage)

        self.channelLabel = QtWidgets.QLabel(text='Channel:')
        self.channelComboBoxWidget = QtWidgets.QComboBox()
        self.channelComboBoxWidget.setFixedWidth(150)
        self.channelComboBoxWidget.currentTextChanged.connect(self.changeChannel)

        self.annotationGroupBox = QtWidgets.QGroupBox('Annotation')
        self.annotateGroupBoxLayout = QtWidgets.QHBoxLayout()
        self.annotationGroupBox.setLayout(self.annotateGroupBoxLayout)

        self.annotateNoneRadioButton = QtWidgets.QRadioButton('None')
        self.annotateNoneRadioButton.setChecked(True)
        self.annotateNoneRadioButton.pressed.connect(self.annotateNone)
        self.annotatePositiveRadioButton = QtWidgets.QRadioButton('Positive')
        self.annotatePositiveRadioButton.pressed.connect(self.annotatePositive)
        self.annotateNegativeRadioButton = QtWidgets.QRadioButton('Negative')
        self.annotateNegativeRadioButton.pressed.connect(self.annotateNegative)
        self.deleteAnnotationRadioButton = QtWidgets.QRadioButton('Delete')
        self.deleteAnnotationRadioButton.pressed.connect(self.startDeleteMode)

        self.annotateGroupBoxLayout.addWidget(self.annotateNoneRadioButton)
        self.annotateGroupBoxLayout.addWidget(self.annotatePositiveRadioButton)
        self.annotateGroupBoxLayout.addWidget(self.annotateNegativeRadioButton)
        self.annotateGroupBoxLayout.addWidget(self.deleteAnnotationRadioButton)

        self.loadAnnotationPushButton = QtWidgets.QPushButton(text='Load Annotations')
        self.loadAnnotationPushButton.clicked.connect(self.loadAnnotations)

        self.saveAnnotationPushButton = QtWidgets.QPushButton(text='Save Annotations')
        self.saveAnnotationPushButton.clicked.connect(self.saveAnnotations)

        self.autoLocatePushButton = QtWidgets.QPushButton(text='Auto Find')
        self.autoLocatePushButton.clicked.connect(self.autoLocate)

        self.autoAnnotatePushbutton = QtWidgets.QPushButton(text='Auto Annotate')
        self.autoAnnotatePushbutton.clicked.connect(self.autoAnnotate)

        # Arrange layout
        self.VBlayout = QtWidgets.QVBoxLayout(self)
        self.VBlayout.addWidget(self.viewer)

        self.HBlayout = QtWidgets.QHBoxLayout()
        self.HBlayout.setAlignment(QtCore.Qt.AlignLeft)

        self.HBlayout.addWidget(self.btnLoad)
        self.HBlayout.addWidget(self.channelLabel)
        self.HBlayout.addWidget(self.channelComboBoxWidget)

        self.HBlayout.addWidget(self.annotationGroupBox)
        # self.HBlayout.addWidget(self.loadAnnotationPushButton)
        self.HBlayout.addWidget(self.saveAnnotationPushButton)
        self.HBlayout.addWidget(self.autoLocatePushButton)
        self.VBlayout.addLayout(self.HBlayout)
        self.channels = {}
        self.rect_start = []
        self.annotation_pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 3, QtCore.Qt.SolidLine)
        self.deletingAnnotations = False
        self.annotationType = 'None'
        self.annotations = []
        self.channelGroupBoxes = {}

    def loadImage(self):
        # TODO fix loading new image crashing
        ret = str(QFileDialog.getExistingDirectory(self, "Select directory containing annotations"))
        if len(ret) < 4:
            return
        else:
            if validateDirectoryFormat(ret):
                self.directory = ret
            else:
                QMessageBox.about(self, "Error", "Invalid LCL Record Directory")
                return False
        unique_names, fl = get_unique_names(self.directory)
        selection, ok = QtWidgets.QInputDialog.getItem(
            self, 'Select', 'Image set to annotate:', unique_names)
        self.channels = get_all_paths_and_channels(self.directory, selection, fl)
        for channel in self.channels.keys():
            self.channelComboBoxWidget.addItem(channel)
        if 'Default' in self.channels.keys():
            self.channelComboBoxWidget.setCurrentText('Default')
            self.viewer.setPhoto(QtGui.QPixmap(self.channels['Default']))
        else:
            channel = self.channels.keys()[0]
            self.channelComboBoxWidget.setCurrentText(channel)
            self.viewer.setPhoto(QtGui.QPixmap(self.channels[channel]))
        self.viewer.zoom = 0
        self.annotateNoneRadioButton.setChecked(True)

    def photoClicked(self, pos):
        if self.viewer.dragMode() == QtWidgets.QGraphicsView.NoDrag:
            self.rect_start = [pos.x(), pos.y()]

    def photoReleased(self, pos):
        if self.viewer.dragMode() == QtWidgets.QGraphicsView.NoDrag:
            if self.annotationType in ['Positive', 'Negative']:
                min_x = min(pos.x(), self.rect_start[0])
                min_y = min(pos.y(), self.rect_start[1])
                max_x = max(pos.x(), self.rect_start[0])
                max_y = max(pos.y(), self.rect_start[1])
                self.viewer.scene.addRect(QtCore.QRectF(min_x, min_y, max_x - min_x, max_y - min_y),
                                          self.annotation_pen)
                self.annotations.append((self.annotationType, min_x, min_y, max_x, max_y))
            if self.deletingAnnotations:
                self.deleteAnnotation(pos)
            print(self.annotations)

    def changeChannel(self, channel):
        tf = self.viewer.transform()
        self.viewer.setPhoto(QtGui.QPixmap(os.path.join(self.channels[channel])), True)
        self.viewer.setTransform(tf)

    def annotateNone(self):
        self.viewer.toggleDragMode(True)
        self.deletingAnnotations = False
        self.annotation_pen = QtGui.QColor(0, 0, 0)
        self.annotationType = 'None'
        print('annotating None')

    def annotatePositive(self):
        self.viewer.toggleDragMode(False)
        self.deletingAnnotations = False
        self.annotation_pen = QtGui.QPen(QtGui.QColor(165, 94, 234), 10, QtCore.Qt.SolidLine)
        self.annotationType = 'Positive'
        print('annotating positive')

    def annotateNegative(self):
        self.viewer.toggleDragMode(False)
        self.deletingAnnotations = False
        self.annotation_pen = QtGui.QPen(QtGui.QColor(254, 211, 48), 10, QtCore.Qt.SolidLine)
        self.annotationType = 'Negative'
        print('annotating negative')

    def startDeleteMode(self):
        self.viewer.toggleDragMode(False)
        self.deletingAnnotations = True
        self.annotation_pen = QtGui.QColor(0, 0, 0)
        self.annotationType = 'None'
        print('deleting annotation')

    def deleteAnnotation(self, pos):
        rect = self.viewer.scene.itemAt(pos, QtGui.QTransform())
        if type(rect) != QtWidgets.QGraphicsPixmapItem:
            for annotation in self.annotations:
                if annotation[1] < pos.x() < annotation[3] and annotation[2] < pos.y() < annotation[4]:
                    self.annotations.remove(annotation)
                    print('deleting:', annotation)
                    self.viewer.scene.removeItem(rect)

    def saveAnnotations(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Enter location to save annotations", "", "Pickle files (*.p)")
        if fileName[-2:] != '.p':
            fileName += '.p'
        print('saving annotations...', fileName)
        # build a pickle that has a list of tuples of form ([annotation type], [channel list], [loc_x, loc_y] [array
        # of shape (x, y, channels)])
        save_list = []
        for annotation in self.annotations:
            temp_tuple = (annotation[0], list(self.channels.keys()))
            # Qt and numpy change X and Y...
            annotation_array = np.zeros((annotation[4] - annotation[2], annotation[3] - annotation[1],
                                         len(self.channels.keys())))
            for i, channel in enumerate(self.channels.keys()):
                img = np.array(Image.open(self.channels[channel]))
                annotation_array[:, :, i] = img[annotation[2]:annotation[4], annotation[1]:annotation[3]]
                temp_tuple += (annotation_array,)
            save_list.append(temp_tuple)
        pickle.dump(save_list, open(fileName, 'wb'))
        print('done')

    def addChannelSelections(self, obj_channels):
        colors = [' (RED)', ' (GREEN)', ' (BLUE)']
        for i, (k, v) in enumerate(obj_channels.items()):
            tempGroupBox = QtWidgets.QGroupBox(k + colors[i])
            tempGroupBoxLayout = QtWidgets.QHBoxLayout()
            tempGroupBox.setLayout(tempGroupBoxLayout)
            tempPositiveRadioButton = QtWidgets.QRadioButton('+ Marker')
            tempNegativeRadioButton = QtWidgets.QRadioButton('- Marker')
            tempGroupBoxLayout.addWidget(tempPositiveRadioButton)
            tempGroupBoxLayout.addWidget(tempNegativeRadioButton)
            self.channelGroupBoxes[k] = [tempPositiveRadioButton, tempNegativeRadioButton]
            self.HBlayout.addWidget(tempGroupBox)
        self.HBlayout.addWidget(self.autoAnnotatePushbutton)

    def autoAnnotate(self):
        for k, v in self.channelGroupBoxes.items():
            print(f'{k}: {self.channelGroupBoxes[k][0].isChecked()}, {self.channelGroupBoxes[k][1].isChecked()}')

    def autoLocate(self):
        obj_channels = get_obj_channels(self.directory)
        colors = [QtGui.QColor(255, 0, 0), QtGui.QColor(0, 255, 0), QtGui.QColor(0, 0, 255)]

        for i, [k, v] in enumerate(obj_channels.items()):
            color = colors[i]
            objs = obj_channels[k]
            for obj in objs:
                s = (obj[1].stop - obj[1].start) * (obj[0].stop - obj[0].start)
                if 1E6 > s > 100:
                    self.viewer.scene.addRect(QtCore.QRectF(obj[1].start, obj[0].start, obj[1].stop - obj[1].start
                                                            , obj[0].stop - obj[0].start), color)
        self.addChannelSelections(obj_channels)

    def loadAnnotations(self):
        print('loading annotations...')
        # TODO: finish implementing this
        # fileName, _ = QFileDialog.getSaveFileName(self, "Enter location to load annotations", "", "Pickle files (*.p)")
        # data = pickle.load(open(fileName, 'rb'))
        # for annotation in data:
        #     x, y = annotation[2].shape[1], annotation[2].shape[0]
        #     if annotation[0] == 'Positive':
        #
        #     elif annotation[0] == 'Negative'


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.setGeometry(500, 300, 800, 600)
    window.show()
    sys.exit(app.exec_())
