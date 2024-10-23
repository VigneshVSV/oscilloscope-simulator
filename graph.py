import sys
import threading
import datetime
import os
from collections import deque

current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
sys.path.append(parent_directory)

from PyQt6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QPushButton,
                            QVBoxLayout, QGroupBox, QSizePolicy, 
                            QCheckBox, QSizePolicy, QMainWindow)
from PyQt6.QtCore import pyqtSlot, pyqtSignal
from PyQt6.QtGui import QFont

import matplotlib.pyplot as plt 
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as PlotNavigationToolbar
import matplotlib.dates as mdates

from hololinked.client import ObjectProxy
from gentec_energy_meters.extensions import GentecMaestroEnergyMeter # This import is optional, but it will help you with code
# editor suggestions or type definitions

def requestProcessID(app_name):
    """
    On Windows, all Python processes receive Python.exe icon (or
    Spyder icon). Setting the AppID will cause Windows to treat as own group
    of processes, so showing correct AppIcon.
    https://stackoverflow.com/questions/1551605/how-to-set-applications-taskbar-icon-in-windows-7/1552105#1552105
    """
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_name)

requestProcessID('sample_gui')



class PlotCanvas(FigureCanvas):

    def __init__(self, parent=None):
        self.figure, self.axis = plt.subplots(1, 1)
        self.line, = plt.plot([], [], label='Energy', marker='s', 
                              linestyle='-', markersize=2)
        
        self.axis.set_xlabel('Timestamp [HH:MM:SS.fff]', fontsize=14)
        self.axis.set_ylabel('Energy [J]',fontsize=14)
        self.axis.set_title('Pulse Energy vs Time', fontsize=14)
        
        self.axis.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S.%f'))
        # self.axis.xaxis.set_major_locator(mdates.SecondLocator(interval=1))
        self.figure.autofmt_xdate()
        
        plt.tight_layout()
        plt.legend()
        plt.grid(True)
            
        FigureCanvas.__init__(self, self.figure)
        self.setParent(parent)   
        self.parent_instance = parent
        FigureCanvas.setSizePolicy(self, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        FigureCanvas.updateGeometry(self)
        


class GentecMaestroUI(QMainWindow):

    statusUpdateSig = pyqtSignal(str)
    plotUpdateSig = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.plotUpdateLock = threading.Lock()
        self.energy_meter_proxy = None 
        
        self._energy_data = deque(maxlen=50) # container of energy data until the last value
        self._timestamps = deque(maxlen=50) # container of timestamps until the last value
        self._new_data_ready = False # flag to inform graph if new data is available so that it can redraw 
        self._plot_count = 0 # indicates a refresh has happened
        self._update_plot = True #
        self.setupUI()
        self.initUI()
        self.plotCanvas.figure.tight_layout()
        self.connectDevice()
        self.show()

    def setupUI(self):
        self.setWindowTitle("Gentec Maestro Energy Meter")

        font = QFont()
        font.setPointSize(10)
        font.setFamily("DejaVu Sans")
        self.setFont(font)
        
        self.mainLayout = QHBoxLayout()

        self.plotLayout = QVBoxLayout()
        self.plotCanvas = PlotCanvas(parent=self)
        self.plotLayout.addWidget(self.plotCanvas)

        self.controlWidget = QGroupBox(self)
        self.controlWidgetLayout = QHBoxLayout(self.controlWidget)
        self.controlWidget.setTitle("Controls")
        self.controlWidget.setLayout(self.controlWidgetLayout)
        
        self.startAcquisitionButton = QPushButton(self.controlWidget)
        self.startAcquisitionButton.setText('Start Acquisition')
        self.controlWidgetLayout.addWidget(self.startAcquisitionButton)

        self.stopAcquisitionButton = QPushButton(self.controlWidget)
        self.stopAcquisitionButton.setText('Stop Acquisition')
        self.controlWidgetLayout.addWidget(self.stopAcquisitionButton)

        self.plotUpdateCheckBox = QCheckBox(self.controlWidget)
        self.plotUpdateCheckBox.setText('update plot')
        self.plotUpdateCheckBox.setChecked(self._update_plot)
        self.controlWidgetLayout.addWidget(self.plotUpdateCheckBox)

        self.plotAutoScaleXAxis = QCheckBox(self.controlWidget)
        self.plotAutoScaleXAxis.setText('Autoscale X axis')
        self.plotAutoScaleXAxis.setChecked(False)
        self.controlWidgetLayout.addWidget(self.plotAutoScaleXAxis)

        self.plotLayout.addWidget(self.controlWidget)
        plotWidget = QWidget(self)
        plotWidget.setLayout(self.plotLayout)
        self.mainLayout.addWidget(plotWidget)

        # self.settingsWidget = QGroupBox(self)
        # self.settingsWidgetLayout = QVBoxLayout(self.settingsWidget)
        # self.settingsWidget.setTitle("Settings")
        # self.settingsWidget.setLayout(self.settingsWidgetLayout)

        # self.triggerLevelInput = QLineEdit(self.settingsWidget)
        # self.triggerLevelInput.setValidator(QDoubleValidator())
        # self.settingsWidgetLayout.addWidget(self.triggerLevelInput)

        # self.applyTriggerLevelButton = QPushButton(self.settingsWidget)
        # self.applyTriggerLevelButton.setText('Apply')
        # self.settingsWidgetLayout.addWidget(self.applyTriggerLevelButton)
        # self.applyTriggerLevelButton.clicked.connect(self.applyTriggerLevel)

        # self.mainLayout.addWidget(self.settingsWidget)

        self.mainWidget = QWidget()
        self.mainWidget.setLayout(self.mainLayout)
        self.setCentralWidget(self.mainWidget)
       
        self.plotToolbar = PlotNavigationToolbar(self.plotCanvas)
        self.controlWidgetLayout.addWidget(self.plotToolbar)


    def initUI(self):
        self.startAcquisitionButton.clicked.connect(self.startAcquisition)
        self.stopAcquisitionButton.clicked.connect(self.stopAcquisition)
        self.plotUpdateCheckBox.clicked.connect(self.changeUpdatingPlots)
        
        self.plotUpdateSig.connect(self.animationLoop)


    def refresh(self):
        pass
              
    def connectDevice(self):
        print("Connecting to device, GUI will close if connection not established")
        self.energy_meter_proxy = ObjectProxy(
                instance_name='gentec-maestro', 
                zmq_protocols='IPC' # zmq protocol set in server.py
            ) # type: GentecMaestroEnergyMeter
    
        self.setupDeviceRead()

    def setupDeviceRead(self):
        self.deviceDataReadyEvent = self.energy_meter_proxy.subscribe_event('data-point-event', 
                                                                       callbacks=[self.updateDataFromDevice])
                                                                        
    def startAcquisition(self):
        self.energy_meter_proxy.start_acquisition()
    
    def stopAcquisition(self):
        self.energy_meter_proxy.stop_acquisition()
        

    def updateDataFromDevice(self, event_data):
        if self._update_plot:
            print("Data received")
            self.plotUpdateLock.acquire()
            self._energy_data.append(event_data["energy"])
            self._timestamps.append(datetime.datetime.strptime(event_data["timestamp"], "%H:%M:%S.%f"))
            # print(self._timestamps)
            # print(self._energy_data)
            self.plotCanvas.line.set_data(self._timestamps, self._energy_data)
            self._new_data_ready = True
            self._plot_count += 1
            self.plotUpdateLock.release() 
            self.plotUpdateSig.emit(self._plot_count)


    @pyqtSlot(int)
    def animationLoop(self, dummyCounter):
        self.plotUpdateLock.acquire()
        if self._new_data_ready:
            if self._timestamps and self.plotAutoScaleXAxis.isChecked():
                self.plotCanvas.axis.set_xlim(self._timestamps[0], self._timestamps[-1])
            self.plotCanvas.figure.canvas.draw()
            print("plotting")
            self._new_data_ready = False # reset flag
        self.plotUpdateLock.release()
       
    def changeUpdatingPlots(self):
        self._update_plot = self.plotUpdateCheckBox.isChecked()

    def applyTriggerLevel(self):
        self.energy_meter_proxy.trigger_level = float(self.triggerLevelInput.text())



if __name__ == '__main__':
    app = None
    app = QApplication(sys.argv)
    UI = GentecMaestroUI()
    sys.exit(app.exec())
