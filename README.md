# Oscilloscope Simulator

An example for an oscilloscope simulator device along with a GUI in PyQt.

For a web GUI, visit [here](https://thing-control-panel.hololinked.dev/#https://examples.hololinked.dev/simulations/oscilloscope/resources/wot-td)
and for server only visit [here](https://examples.hololinked.dev/simulations/oscilloscope/resources/wot-td).
PyQt GUI is a standalone application that can be run on a local machine.

Currently this repository is used for speed-tests of JSON implementation (probably in future also other serialization protocols) and an online live example.

Docker image is available, just do: <br />
`docker pull ghcr.io/vigneshvsv/oscilloscope-simulator:main` <br />
for the latest image.

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/VigneshVSV/oscilloscope-simulator/docker-publish.yml?label=Build%20Docker%20Image)


Following environment variables are necessary in a docker container:
- `hostname` - hostname of the server
- `ssl_used` - optional, pythonic evaluated as a boolean (satisfies if condition for any type) if your server has SSL setup 
- `use_ssl` - optional, supply a certificate and key file under an assets folder for creating a SSL context 
- `port` - optional, port number of the server if a registered domain is not used in hostname, default 5000 for `localhost`

These variables are necessary for the forms to be correctly generated in a [Thing Description](https://www.w3.org/TR/wot-thing-description11/) otherwise the device will still work, but the forms will be wrong. These environment variables are not necessary if you are running the server outside docker. 

### Dependencies

PyQt6, pyqtgraph, matplotlib (optional), numpy, hololinked

`pip install PyQt6 pyqtgraph numpy hololinked`

### To run

- Go to server.py and run the script. 
- Go to graph.py and run the script to show the PyQt GUI.
- speed-test.py prints speed test for script-only access (i.e. without plotting which takes its own extra time)

#### Result

###### Access speed

just acccess all 4 channels + x axis (time axis)

|number of elements per array | msgspec | python's own json |
|------------|---------|---------|
|1e3| 5.1ms   | 8.7ms |
|1e4| 10.3ms  | 36ms  |
|1e5| 73.2ms  | 326ms |

1e3 means 1000 elements per array, which means that for 4 channels and time axis there are totally 5000 elements. 

###### Preview speed

Access all 4 channels and x axis (time axis), but plot only one channel

|number of elements per array | msgspec | python's own json |
|----------------------|---------|---------|
|1e3| 63FPS | 49FPS |
|1e4| 30FPS | 13FPS |
|1e5| 4.5FPS | 1.7FPS |

Processor speed - 3.8 to 4GHz approx

### Preview

![Image 1](results/msgspec-1000.png) 

Autoscale Y Axis dont work yet
