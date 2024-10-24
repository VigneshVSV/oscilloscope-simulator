# Oscilloscope Simulator

Small example for a oscilloscope simulator device along with a GUI in PyQt.

Currently used for speed-tests of JSON implementation (probably in future also other serialization protocols).

### Dependencies

PyQt6, pyqtgraph, matplotlib (optional), numpy, hololinked

`pip install PyQt6 pyqt pyqtgraph numpy hololinked`

### To run

- Go to server.py and run the script. 
- Go to graph.py and run the script to show the GUI.
- speed-test.py prints speed test for script-only access (i.e. without plotting which takes its own extra time)

###### Result

Access speed - (4 channels + x axis or time axis)

|number of elements per array | msgspec | python's own json |
|------------|---------|---------|
|1e3| 5.1ms   | 8.7ms |
|1e4| 10.3ms  | 36ms  |
|1e5| 73.2ms  | 326ms |

Access all 4 channels and x axis (time axis), but plot only one channel

|number of elements per array | msgspec | python's own json |
|----------------------|---------|---------|
|1e3| 63FPS | 49FPS |
|1e4| 30FPS | 13FPS |
|1e5| 4.5FPS | 1.7FPS |

### Preview

![Image 1](results/msgspec-1000.png) 

Autoscale Y Axis dont work yet