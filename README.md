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

| msgspec | python's own json |
|---------|---------|
| ![Image 1](results/msgspec-1000.png) | ![Image 2](results/python-json-1000) |
| ![Image 3](results/msgspec-10000.png) | ![Image 4](results/python-json-10000) |
| ![Image 5](results/msgspec-100000.png) | ![Image 6](results/python-json-100000) |