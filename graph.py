import json
import sys
import threading
import time
import pyqtgraph as pg
from PyQt6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QPushButton, QLabel,
                            QVBoxLayout, QGroupBox, QSizePolicy, QLineEdit, QComboBox,
                            QCheckBox, QSizePolicy, QMainWindow)
from PyQt6.QtCore import pyqtSlot, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QDoubleValidator, QIntValidator
from hololinked.client import ObjectProxy

try:
    import matplotlib.pyplot as plt 
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as PlotNavigationToolbar
except ImportError:
    print("Matplotlib not installed, please install if you want to use matplotlib plotting")


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
        self.line, = plt.plot([], [], label='Trace', marker='s', 
                              linestyle='-', markersize=2)
        
        self.axis.set_xlabel('Time [s]', fontsize=14)
        self.axis.set_ylabel('Trace [Arbitrary Units]',fontsize=14)
        self.axis.set_title('Trace vs Time', fontsize=14)
        self.axis.set_xlim(0, 1)
        self.axis.set_ylim(-1, 100)
           
        plt.tight_layout()
        plt.legend()
        plt.grid(True)
            
        FigureCanvas.__init__(self, self.figure)
        self.setParent(parent)   
        self.parent_instance = parent
        FigureCanvas.setSizePolicy(self, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        FigureCanvas.updateGeometry(self)
        


class OscilloscopeSimulator(QMainWindow):

    plotUpdateSig = pyqtSignal(int)
    fpsUpdateSig = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self._plot_update_lock = threading.Lock()
        self._acquisition_continue = threading.Event()
        self._thread = None
        self.oscilloscope_proxy = None 
        
        self._new_data_ready = False # flag to inform graph if new data is available so that it can redraw 
        self._plot_count = 0 # indicates a refresh has happened
        self._update_plot = True #
        self.setupUI()
        self.initUI()
        # self.plotCanvas.figure.tight_layout() # uncomment for matplotlib
        self.connectDevice()
        self.setupDeviceRead()
        self.switchDevice('msgspec-json')
        self.refresh()
        self.show()


    def setupUI(self):
        self.setWindowTitle("Oscilloscope Simulator")

        font = QFont()
        font.setPointSize(10)
        font.setFamily("DejaVu Sans")
        self.setFont(font)
        
        self.mainLayout = QHBoxLayout()

        self.plotLayout = QVBoxLayout()
        # self.plotCanvas = PlotCanvas(parent=self) # uncomment for matplotlib
        # self.plotLayout.addWidget(self.plotCanvas)
        self.plotCanvas = pg.PlotWidget(self)
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

        self.fpsLabel = QLabel(self.controlWidget)
        self.fpsLabel.setText('FPS: 0')
        self.controlWidgetLayout.addWidget(self.fpsLabel)

        self.plotLayout.addWidget(self.controlWidget)
        plotWidget = QWidget(self)
        plotWidget.setLayout(self.plotLayout)
        self.mainLayout.addWidget(plotWidget)

        # self.plotToolbar = PlotNavigationToolbar(self.plotCanvas) # uncomment for matplotlib
        # self.controlWidgetLayout.addWidget(self.plotToolbar)

        self.settingsWidget = QGroupBox(self)
        self.settingsWidgetLayout = QVBoxLayout(self.settingsWidget)
        self.settingsWidget.setTitle("Settings")
        self.settingsWidget.setLayout(self.settingsWidgetLayout)

        self.deviceSwitchLabel = QLabel("Select Device", self.settingsWidget)
        self.settingsWidgetLayout.addWidget(self.deviceSwitchLabel)

        self.deviceSwitchDropdown = QComboBox(self.settingsWidget)
        self.deviceSwitchDropdown.addItems(['msgspec-json', 'python-json'])
        self.deviceSwitchDropdown.currentTextChanged.connect(self.switchDevice)
        self.settingsWidgetLayout.addWidget(self.deviceSwitchDropdown)

        self.timeRangeInputLabel = QLabel("Time Range (s)", self.settingsWidget)
        self.settingsWidgetLayout.addWidget(self.timeRangeInputLabel)

        self.timeRangeInput = QLineEdit(self.settingsWidget)
        self.timeRangeInput.setValidator(QDoubleValidator())
        self.settingsWidgetLayout.addWidget(self.timeRangeInput)

        self.timeResolutionInputLabel = QLabel("Time Resolution (s)", self.settingsWidget)
        self.settingsWidgetLayout.addWidget(self.timeResolutionInputLabel)

        self.timeResolutionInput = QLineEdit(self.settingsWidget)
        self.timeResolutionInput.setValidator(QDoubleValidator())
        self.settingsWidgetLayout.addWidget(self.timeResolutionInput)

        self.valueRangeInputLabel = QLabel("Value Range (V)\n(enter JSON)", self.settingsWidget)
        self.settingsWidgetLayout.addWidget(self.valueRangeInputLabel)

        self.valueRangeInput = QLineEdit(self.settingsWidget)
        self.settingsWidgetLayout.addWidget(self.valueRangeInput)

        self.applySettingsButton = QPushButton(self.settingsWidget)
        self.applySettingsButton.setText('Apply')
        self.settingsWidgetLayout.addWidget(self.applySettingsButton)
        self.applySettingsButton.clicked.connect(self.applySettings)

        self.settingsWidgetLayout.addStretch(1)

        self.numberOfSamplesInputLabel = QLabel("Number of Samples", self.settingsWidget)
        self.settingsWidgetLayout.addWidget(self.numberOfSamplesInputLabel)

        self.numberOfSamplesInput = QLineEdit(self.settingsWidget)
        self.numberOfSamplesInput.setValidator(QIntValidator())
        self.numberOfSamplesInput.setText('1')
        self.settingsWidgetLayout.addWidget(self.numberOfSamplesInput)
       
        self.mainLayout.addWidget(self.settingsWidget)

        self.xLimitsLabel = QLabel("X Limits (min, max)", self.settingsWidget)
        self.settingsWidgetLayout.addWidget(self.xLimitsLabel)
        self.xLimitsLayout = QHBoxLayout()

        self.xMinInput = QLineEdit(self.settingsWidget)
        self.xMinInput.setValidator(QDoubleValidator())
        self.xMinInput.setText('0')
        self.xLimitsLayout.addWidget(self.xMinInput)

        self.xMaxInput = QLineEdit(self.settingsWidget)
        self.xMaxInput.setValidator(QDoubleValidator())
        self.xMaxInput.setText('1')
        self.xLimitsLayout.addWidget(self.xMaxInput)

        self.plotAutoScaleXAxis = QCheckBox(self.controlWidget)
        self.plotAutoScaleXAxis.setText('Autoscale X axis')
        self.plotAutoScaleXAxis.setChecked(True)
        self.settingsWidgetLayout.addWidget(self.plotAutoScaleXAxis)

        self.settingsWidgetLayout.addLayout(self.xLimitsLayout)

        self.yLimitsLabel = QLabel("Y Limits (min, max)", self.settingsWidget)
        self.settingsWidgetLayout.addWidget(self.yLimitsLabel)
        self.yLimitsLayout = QHBoxLayout()

        self.yMinInput = QLineEdit(self.settingsWidget)
        self.yMinInput.setValidator(QDoubleValidator())
        self.yMinInput.setText('0')
        self.yLimitsLayout.addWidget(self.yMinInput)

        self.yMaxInput = QLineEdit(self.settingsWidget)
        self.yMaxInput.setValidator(QDoubleValidator())
        self.yMaxInput.setText('1')
        self.yLimitsLayout.addWidget(self.yMaxInput)
        self.settingsWidgetLayout.addLayout(self.yLimitsLayout)

        self.plotAutoScaleYAxis = QCheckBox(self.controlWidget)
        self.plotAutoScaleYAxis.setText('Autoscale Y axis')
        self.plotAutoScaleYAxis.setChecked(True)
        self.settingsWidgetLayout.addWidget(self.plotAutoScaleYAxis)

        self.applyAxisLimitsButton = QPushButton(self.settingsWidget)
        self.applyAxisLimitsButton.setText('Apply Axis Limits')
        self.applyAxisLimitsButton.clicked.connect(self.updateAxisLimits)

        self.plotUpdateCheckBox = QCheckBox(self.controlWidget)
        self.plotUpdateCheckBox.setText('update plot')
        self.plotUpdateCheckBox.setChecked(self._update_plot)
        self.settingsWidgetLayout.addWidget(self.plotUpdateCheckBox)

        self.settingsWidgetLayout.addWidget(self.applyAxisLimitsButton)
        self.updateAxisLimits()

        self.settingsWidget.setMaximumWidth(175)
        self.controlWidget.setMinimumWidth(175*4)
        self.mainWidget = QWidget()
        self.mainWidget.setLayout(self.mainLayout)
        self.setCentralWidget(self.mainWidget)


    def initUI(self):
        self.startAcquisitionButton.clicked.connect(self.startAcquisition)
        self.stopAcquisitionButton.clicked.connect(self.stopAcquisition)
        self.plotUpdateCheckBox.clicked.connect(self.changeUpdatingPlots)        
        self.plotUpdateSig.connect(self.animationLoop)
        self.fpsUpdateSig.connect(self.updateFPS)

    def closeEvent(self, event):
        self.oscilloscope_proxy_msgspec_json.unsubscribe_event('data-ready-event')
        self.oscilloscope_proxy_python_json.unsubscribe_event('data-ready-event')
        event.accept()

    def refresh(self):
        self.timeRangeInput.setText(str(self.oscilloscope_proxy.time_range))
        self.timeResolutionInput.setText(str(self.oscilloscope_proxy.time_resolution))
        self.valueRangeInput.setText(str(self.oscilloscope_proxy.value_range))

    def connectDevice(self):
        print("Connecting to device, GUI will close if connection not established")
        self.oscilloscope_proxy_python_json = ObjectProxy(
                instance_name='oscilloscope-sim-python-json', 
                zmq_protocols='IPC' # zmq protocol set in server.py
            ) 
        self.oscilloscope_proxy_msgspec_json = ObjectProxy(
            instance_name='oscilloscope-sim-msgspec-json', 
            zmq_protocols='IPC' # zmq protocol set in server.py
        )     
        self.current_device = self.oscilloscope_proxy_msgspec_json
        
    @pyqtSlot(str)
    def switchDevice(self, option):
        is_none = True
        if self.oscilloscope_proxy is not None:
            is_none = False
            state = self.oscilloscope_proxy.state
            if state == 'RUNNING':
                self.oscilloscope_proxy.stop()
            time_range = self.oscilloscope_proxy.time_range
            time_resolution = self.oscilloscope_proxy.time_resolution
            value_range = self.oscilloscope_proxy.value_range
        if option == 'msgspec-json':
            self.oscilloscope_proxy = self.oscilloscope_proxy_msgspec_json
        elif option == 'python-json':
            self.oscilloscope_proxy = self.oscilloscope_proxy_python_json
        if not is_none:
            self.oscilloscope_proxy.time_range = time_range
            self.oscilloscope_proxy.time_resolution = time_resolution
            self.oscilloscope_proxy.value_range = value_range
        print(f"Switched to {option}")
        self.refresh()

    def setupDeviceRead(self):
        self.oscilloscope_proxy_msgspec_json.subscribe_event('data-ready-event', 
                                                            callbacks=[self.updateDataFromDevice])
        self.oscilloscope_proxy_python_json.subscribe_event('data-ready-event', 
                                                            callbacks=[self.updateDataFromDevice])
        
                                                                        
    def startAcquisition(self):
        # Create QThread and worker instance
        if self._thread is not None and self.worker._run: # dont depend on inner isRunning method
            print("Acquisition already running")
            return
        self._thread = QThread(parent=self)
        self.worker = AcquisitionWorker(self.oscilloscope_proxy, 
                                    int(self.numberOfSamplesInput.text()), 
                                    self._acquisition_continue,
                                    self.fpsUpdateSig
                                )
        # Move the worker to the thread
        self.worker.moveToThread(self._thread)
        # Connect the signals and slots
        self._thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._thread.quit)  # Stop the thread when done
        self.worker.finished.connect(self.worker.deleteLater)  # Cleanup worker
        self._thread.finished.connect(self._thread.deleteLater)  # Cleanup thread
        # Start the thread
        self._thread.start()
       
    def stopAcquisition(self):
        try:
            self.worker.stop_run()
        except:
            pass


    def updateDataFromDevice(self, event_data):
        self._plot_count += 1
        if self._update_plot:
            print("Data received", event_data)
            self._plot_update_lock.acquire()
            self._x_axis = self.oscilloscope_proxy.x_axis
            self._channel_A = self.oscilloscope_proxy.channel_A   
            self._channel_B = self.oscilloscope_proxy.channel_B
            self._channel_C = self.oscilloscope_proxy.channel_C
            self._channel_D = self.oscilloscope_proxy.channel_D
            # self.plotCanvas.line.set_data(self._x_axis, self._channel_A) # uncomment for matplotlib
            self._new_data_ready = True
            self._plot_update_lock.release() 
        self.plotUpdateSig.emit(self._plot_count)


    @pyqtSlot(int)
    def animationLoop(self, dummyCounter):
        self._plot_update_lock.acquire()
        if self._new_data_ready:
            # if self._x_axis and self.plotAutoScaleXAxis.isChecked(): # uncomment for matplotlib
            #     self.plotCanvas.axis.set_xlim(self._x_axis[0], self._x_axis[-1])
            # self.plotCanvas.figure.canvas.draw()
            self.plotCanvas.clear()
            self.plotCanvas.plot(self._x_axis, self._channel_A, pen=pg.mkPen(color='r', width=2))  # Red line
            if self.plotAutoScaleXAxis.isChecked():
                self.plotCanvas.setXRange(self._x_axis[0], self._x_axis[-1])
            QApplication.processEvents() 
            print("plotting")
            self._new_data_ready = False # reset flag
        self._plot_update_lock.release()
        self._acquisition_continue.set()
       
       
    def changeUpdatingPlots(self):
        self._update_plot = self.plotUpdateCheckBox.isChecked()

    def updateAxisLimits(self):
        x_min = float(self.xMinInput.text())
        x_max = float(self.xMaxInput.text())
        y_min = float(self.yMinInput.text())
        y_max = float(self.yMaxInput.text())
        self.plotCanvas.setXRange(x_min, x_max)
        self.plotCanvas.setYRange(y_min, y_max)

    def updateFPS(self, fps):
        self.fpsLabel.setText(f"FPS: {fps:.2f}")

    def applySettings(self):
        self.oscilloscope_proxy.time_range = float(self.timeRangeInput.text())
        self.oscilloscope_proxy.time_resolution = float(self.timeResolutionInput.text())
        self.oscilloscope_proxy.value_range = json.loads(self.valueRangeInput.text())
        self.refresh()



class AcquisitionWorker(QThread):
    def __init__(self, oscilloscope_proxy, number_of_samples, acquisition_continue, fps_sig):
        super().__init__()
        self._run = True
        self._fps = 0
        self.oscilloscope_proxy = oscilloscope_proxy
        self.number_of_samples = number_of_samples
        self.acquisition_continue = acquisition_continue
        self.fps_sig = fps_sig

    def run(self):
        print("Starting acquisition")
        start_time = time.time()
        frame_count = 0
        for i in range(self.number_of_samples):
            QApplication.processEvents() # allow GUI to update, complete pending plots
            if not self._run:
                break
            self.oscilloscope_proxy.start(max_count=1)
            self.acquisition_continue.wait()
            self.acquisition_continue.clear()
            # time.sleep(0.02) # limit to max 50FPS even if plotting takes only 1ms

            frame_count += 1
            current_time = time.time()
            elapsed_time = current_time - start_time
            if elapsed_time >= 1.0:
                self._fps = frame_count / elapsed_time
            self.fps_sig.emit(self._fps)
        self._run = False
        print("Finished acquisition")

    def stop_run(self):
        self._run = False
        


if __name__ == '__main__':
    app = None
    app = QApplication(sys.argv)
    UI = OscilloscopeSimulator()
    sys.exit(app.exec())
