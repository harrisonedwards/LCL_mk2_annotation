import os
import pickle
import sys
import numpy as np
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from utils import get_unique_names, get_all_paths_and_channels, get_obj_channels, validateDirectoryFormat
import sip

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
        self.showMaximized()
        
        self.directory = None

        self.viewer = PhotoViewer(self)
        self.viewer.photoClicked.connect(self.photoClicked)
        self.viewer.photoReleased.connect(self.photoReleased)

        # 'Load image' button
        self.btnLoad = QtWidgets.QToolButton(self)
        self.btnLoad.setText('Open Image\nDirectory')
        self.btnLoad.clicked.connect(self.loadImage)

        self.removeRectPushbutton = QtWidgets.QPushButton(text='Delete Rectangles\nand Annotations')
        self.removeRectPushbutton.clicked.connect(self.removeAllRects)

        self.channelLabel = QtWidgets.QLabel(text='Channel:')
        self.channelComboBoxWidget = QtWidgets.QComboBox()
        self.channelComboBoxWidget.setFixedWidth(150)
        self.channelComboBoxWidget.currentTextChanged.connect(self.changeChannel)
        self.annotationGroupBox = QtWidgets.QGroupBox('Annotation')
        self.annotateGroupBoxLayout = QtWidgets.QHBoxLayout()
        self.annotationGroupBox.setLayout(self.annotateGroupBoxLayout)

        self.annotateNoneRadioButton = QtWidgets.QRadioButton('Drag Mode')
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

        self.loadAnnotationPushButton = QtWidgets.QPushButton(text='Load\nAnnotations')
        self.loadAnnotationPushButton.clicked.connect(self.loadAnnotations)

        self.saveAnnotationPushButton = QtWidgets.QPushButton(text='Save\nAnnotations')
        self.saveAnnotationPushButton.clicked.connect(self.saveAnnotations)

        self.autoLocatePushButton = QtWidgets.QPushButton(text='Auto\nFind')
        self.autoLocatePushButton.clicked.connect(self.autoLocate)

        self.autoAnnotatePushbutton = QtWidgets.QPushButton(text='Auto\nAnnotate')
        self.autoAnnotatePushbutton.clicked.connect(self.snapToDapiLoc)

        # Arrange layout
        self.VBlayout = QtWidgets.QVBoxLayout(self)
        self.VBlayout.addWidget(self.viewer)
        self.HBlayout = QtWidgets.QHBoxLayout()
        self.HBlayout.setAlignment(QtCore.Qt.AlignLeft)
        self.HBlayout.addWidget(self.btnLoad)
        self.HBlayout.addWidget(self.channelLabel)
        self.HBlayout.addWidget(self.channelComboBoxWidget)


        # self.HBlayout.addWidget(self.loadAnnotationPushButton)

        self.VBlayout.addLayout(self.HBlayout)
        self.channels = {}
        self.rect_start = []
        self.annotation_pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 3, QtCore.Qt.SolidLine)
        self.deletingAnnotations = False
        self.annotationType = 'None'
        self.annotations = []
        self.meta_annotations = []
        self.channelGroupBoxes = {}
        self.channelSliders = {}
        self.obj_channels = None
        self.locatedObjectsComboBox = QtWidgets.QComboBox()
        self.locatedObjectsComboBox.currentTextChanged.connect(self.snapToDapiLoc)
        self.annotationAssistPushButton = QtWidgets.QPushButton('Assisted\nAnnotation')
        self.annotationAssistPushButton.setCheckable(True)
        self.annotationAssistPushButton.clicked.connect(self.toggleAssistedAnnotation)
        self.trackingAnnotations = False

    def stopAssistedAnnotation(self):
        self.viewer.toggleDragMode(True)
        self.annotateNoneRadioButton.setEnabled(True)
        self.locatedObjectsComboBox.setEnabled(False)
        self.annotationAssistPushButton.setChecked(False)
        # set it so we can zoom on mouse
        self.viewer.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.viewer.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        # change the color of the toggle
        self.annotationAssistPushButton.setStyleSheet("background-color : lightgrey")
        self.trackingAnnotations = False

    def startAssistedAnnotation(self):
        text = self.locatedObjectsComboBox.currentText()
        if text == '':
            return
        self.viewer.toggleDragMode(False)
        self.annotateNoneRadioButton.setEnabled(False)
        # add the list of auto located dapi things
        self.locatedObjectsComboBox.setEnabled(True)
        # go to the first index of the auto located things


        self.snapToDapiLoc(text)
        # set it so we can only zoom directly in and out
        self.viewer.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        self.viewer.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        # change the color of the toggle
        self.annotationAssistPushButton.setStyleSheet("background-color : lightblue")
        self.trackingAnnotations = True

    def toggleAssistedAnnotation(self):
        if self.annotationAssistPushButton.isChecked():
            self.startAssistedAnnotation()
        elif not self.annotationAssistPushButton.isChecked():
            self.stopAssistedAnnotation()



    def autoLocate(self):
        self.removeAllRects()
        self.stopAssistedAnnotation()
        self.locatedObjectsComboBox.clear()
        if self.channelGroupBoxes != {}:
            # if we do have channel group boxes
            channelThreshValues = self.getSliderValues(None)
            self.removeChannelGroupBoxes()
            self.obj_channels, channelThreshValues = get_obj_channels(self.directory, channelThreshValues)
        elif self.channelGroupBoxes == {}:
            # if we dont have channel group boxes
            self.obj_channels, channelThreshValues = get_obj_channels(self.directory)
        colors = [QtGui.QColor(255, 0, 0), QtGui.QColor(0, 255, 0), QtGui.QColor(0, 0, 255), QtGui.QColor(102, 51, 0)]
        temp_items = {}
        for i, [k, v] in enumerate(self.obj_channels.items()):
            color = colors[i]
            objs = self.obj_channels[k]
            temp_items[k] = []
            for obj in objs:
                s = (obj[1].stop - obj[1].start) * (obj[0].stop - obj[0].start)
                # filter out super large and super small boxes
                if 1E6 > s > 100:
                    self.viewer.scene.addRect(QtCore.QRectF(obj[1].start, obj[0].start, obj[1].stop - obj[1].start
                                                            , obj[0].stop - obj[0].start), color)
                    temp_items[k].append(obj)
        self.obj_channels = temp_items
        self.addChannelSelections(channelThreshValues)
        self.HBlayout.addWidget(self.annotationAssistPushButton)
        self.HBlayout.addWidget(self.locatedObjectsComboBox)
        self.locatedObjectsComboBox.setEnabled(False)

    def snapToDapiLoc(self, text):
        if self.annotationAssistPushButton.isChecked():
            x, y = int(text.split(', ')[0]), int(text.split(', ')[1])
            self.viewer.centerOn(x, y)

    def startAnnotating(self):
        # add all of the necessary GUI elements for annotating
        self.HBlayout.addWidget(self.annotationGroupBox)
        self.HBlayout.addWidget(self.saveAnnotationPushButton)
        self.HBlayout.addWidget(self.autoLocatePushButton)
        self.HBlayout.addWidget(self.removeRectPushbutton)

    def loadImage(self):
        # reset the gui for new image
        self.removeAllRects()
        self.channelComboBoxWidget.clear()
        if self.channelGroupBoxes != {}:
            self.removeChannelGroupBoxes()
        # now setup gui with new image
        ret = str(QFileDialog.getExistingDirectory(self, "Select directory containing images for annotation"))
        if ret == '':
            return
        if not validateDirectoryFormat(ret):
            QMessageBox.about(self, "Error", "Invalid LCL Record Directory")
            return False
        self.directory = ret
        self.channels = get_all_paths_and_channels(self.directory)
        for channel in self.channels.keys():
            self.channelComboBoxWidget.addItem(channel)
        if 'Default' in self.channels.keys():
            self.channelComboBoxWidget.setCurrentText('Default')
            self.viewer.setPhoto(QtGui.QPixmap(self.channels['Default']))
        else:
            channel = list(self.channels.keys())[0]
            self.channelComboBoxWidget.setCurrentText(channel)
            self.viewer.setPhoto(QtGui.QPixmap(self.channels[channel]))
        self.viewer.zoom = 0
        self.annotateNoneRadioButton.setChecked(True)
        self.startAnnotating()

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

                if self.trackingAnnotations:
                    ul = self.viewer.mapToScene(self.rect().topLeft())
                    br = self.viewer.mapToScene(self.rect().bottomRight())
                    zoom = self.viewer.zoom
                    idx = self.locatedObjectsComboBox.currentIndex()
                    obj = self.obj_channels['dapi'][idx]
                    self.meta_annotations.append((zoom, [int(i) for i in [ul.x(), ul.y(), br.x(), br.y()]],
                                                  [(obj[1].stop - obj[1].start) * (obj[0].stop - obj[0].start)]))
                else:
                    QMessageBox.about(self, "Warning", "Meta annotations are currently not being saved! Please enable "
                                                       "annotation assist.")
            if self.deletingAnnotations:
                self.deleteAnnotation(pos)
            print('annotations:', self.annotations)
            print('meta annotations:', self.meta_annotations)

    def changeChannel(self, channel):
        if channel == '':
            return
        tf = self.viewer.transform()
        self.viewer.setPhoto(QtGui.QPixmap(os.path.join(self.channels[channel])), True)
        self.viewer.setTransform(tf)

    def annotateNone(self):
        self.viewer.toggleDragMode(True)
        self.deletingAnnotations = False
        self.annotation_pen = QtGui.QColor(0, 0, 0)
        self.annotationType = 'None'
        print('Dragging Mode')

    def annotatePositive(self):
        self.viewer.toggleDragMode(False)
        self.deletingAnnotations = False
        self.annotation_pen = QtGui.QPen(QtGui.QColor(254, 211, 48), 4, QtCore.Qt.SolidLine)
        self.annotationType = 'Positive'
        print('annotating positive')

    def annotateNegative(self):
        self.viewer.toggleDragMode(False)
        self.deletingAnnotations = False
        self.annotation_pen = QtGui.QPen(QtGui.QColor(165, 94, 234), 4, QtCore.Qt.SolidLine)
        self.annotationType = 'Negative'
        print('annotating negative')

    def startDeleteMode(self):
        self.viewer.toggleDragMode(False)
        self.deletingAnnotations = True
        self.annotation_pen = QtGui.QColor(0, 0, 0)
        self.annotationType = 'None'
        print('deleting annotation')

    def removeAllRects(self):
        # TODO: make this only remove non-annotation rectangles
        self.annotations = []
        self.meta_annotations = []
        for item in self.viewer.scene.items():
            if item.type() == 3:
                self.viewer.scene.removeItem(item)

    def deleteAnnotation(self, pos):
        rect = self.viewer.scene.itemAt(pos, QtGui.QTransform())
        if type(rect) != QtWidgets.QGraphicsPixmapItem:
            if len(self.annotations) == len(self.meta_annotations):
                for i, annotation in enumerate(self.annotations):
                    if annotation[1] < pos.x() < annotation[3] and annotation[2] < pos.y() < annotation[4]:
                        self.annotations.remove(annotation)
                        print('deleting:', annotation)
                        print('and meta annotation:', self.meta_annotations.pop(i))
            else:
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
        # build a pickle that has a list of tuples of form ([annotation type], [channel list],
        # [annotation array of shape (x, y, channels)], [meta_annotation array of shape (x, y, channels)])
        save_list = []
        for annotation, meta_annotation in zip(self.annotations, self.meta_annotations):
            temp_tuple = (annotation[0], list(self.channels.keys()))
            # Qt and numpy change X and Y...
            annotation_array = np.zeros((annotation[4] - annotation[2],
                                         annotation[3] - annotation[1],
                                         len(self.channels.keys())))
            # switching this here to get the actual array
            meta_annotation = meta_annotation[1]
            meta_annotation_array = np.zeros((meta_annotation[3] - meta_annotation[1],
                                              meta_annotation[2] - meta_annotation[0],
                                              len(self.channels.keys())))
            for i, channel in enumerate(self.channels.keys()):
                img = np.array(Image.open(self.channels[channel]))
                annotation_array[:, :, i] = img[annotation[2]:annotation[4], annotation[1]:annotation[3]]
                meta_annotation_array[:, :, i] = img[meta_annotation[1]:meta_annotation[3],
                                                     meta_annotation[0]:meta_annotation[2]]
            temp_tuple += (annotation_array, meta_annotation_array)
            save_list.append(temp_tuple)
        pickle.dump(save_list, open(fileName, 'wb'))
        print('done')

    def getSliderValues(self, _):
        channelThreshValues = {}
        for name, _ in self.obj_channels.items():
            slider = self.findChild(QtWidgets.QSlider, name)
            channelThreshValues[name] = slider.value()
        return channelThreshValues

    def addChannelSelections(self, channelThreshValues):
        colors = [' (RED)', ' (GREEN)', ' (BLUE)', ' (BROWN)']
        for i, (k, _) in enumerate(self.obj_channels.items()):
            # make overall vGroupBox
            tempGroupBox = QtWidgets.QGroupBox(k + colors[i])
            tempGroupBox.setObjectName(k + 'GroupBox')
            tempGroupBoxVLayout = QtWidgets.QVBoxLayout()
            tempGroupBox.setLayout(tempGroupBoxVLayout)
            # make radio button hbox
            # tempRadioButtonHlayout = QtWidgets.QHBoxLayout()
            # tempPositiveRadioButton = QtWidgets.QRadioButton('+ Marker')
            # tempNegativeRadioButton = QtWidgets.QRadioButton('- Marker')
            # tempRadioButtonHlayout.addWidget(tempPositiveRadioButton)
            # tempRadioButtonHlayout.addWidget(tempNegativeRadioButton)
            # make slider widget
            tempSliderWidget = QtWidgets.QSlider(orientation=QtCore.Qt.Horizontal)
            tempSliderWidget.setObjectName(k)
            tempSliderWidget.setMaximum(255)
            tempSliderWidget.setMinimum(0)
            # tempSliderWidget.valueChanged.connect(self.getSliderValues)
            tempSliderWidget.setSliderPosition(int(channelThreshValues[k]))
            # add radio hbox to overall vGroupBox
            # tempGroupBoxVLayout.addLayout(tempRadioButtonHlayout)
            # add slider widget to overall vGroupBox
            tempGroupBoxVLayout.addWidget(tempSliderWidget)
            # self.channelGroupBoxes[k] = [tempPositiveRadioButton, tempNegativeRadioButton]
            self.HBlayout.addWidget(tempGroupBox)
            self.channelSliders[k] = tempSliderWidget
        if self.locatedObjectsComboBox is not None:
            self.HBlayout.removeWidget(self.locatedObjectsComboBox)
        # setup extra gui elements
        # TODO: remove all items first before repopulating
        for obj in self.obj_channels['dapi']:
            x = int(obj[1].start + (obj[1].stop - obj[1].start) / 2)
            y = int(obj[0].start + (obj[0].stop - obj[0].start) / 2)
            self.locatedObjectsComboBox.addItem(f'{x}, {y}')

    def removeChannelGroupBoxes(self):
        for name, _ in self.obj_channels.items():
            groupBox = self.findChild(QtWidgets.QGroupBox, name + 'GroupBox')
            self.HBlayout.removeWidget(groupBox)
            sip.delete(groupBox)
            groupBox = None
            self.channelGroupBoxes = {}
        self.HBlayout.removeWidget(self.autoAnnotatePushbutton)

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


    # window.setGeometry(500, 300, 800, 600)
    window.show()
    sys.exit(app.exec_())
