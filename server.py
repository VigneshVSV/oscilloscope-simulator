import typing
import numpy, threading 
import datetime
from hololinked.server import Thing, action, Property, Event, StateMachine 
from hololinked.server.properties import Number, ClassSelector, Tuple
from hololinked.param import depends_on
from hololinked.server.serializers import JSONSerializer, PythonBuiltinJSONSerializer
from schema import set_trigger_schema



class OscilloscopeSim(Thing):
    """Simulates https://gitlab.com/hololinked-examples/picoscope/-/blob/main/picoscope/pico6000.py"""

    time_resolution = Number(default=1e-6, metadata=dict(unit='s'), bounds=(0, None), step=1e-9,
                            doc='Time resolution of the oscilloscope')

    time_range = Number(default=1e-3, metadata=dict(unit='s'), bounds=(0, None), step=1e-9, 
                    doc='Time range of the oscilloscope')

    channel_A = ClassSelector(doc='Channel A data', class_=(numpy.ndarray,), allow_None=True, default=None,
                            readonly=True, fget=lambda self : self._channel_A)
   
    channel_B = ClassSelector(doc='Channel B data', class_=(numpy.ndarray,), allow_None=True, default=None,
                            readonly=True, fget=lambda self : self._channel_B)
    
    channel_C = ClassSelector(doc='Channel C data', class_=(numpy.ndarray,), allow_None=True, default=None,
                            readonly=True, fget=lambda self : self._channel_C)

    channel_D = ClassSelector(doc='Channel D data', class_=(numpy.ndarray,), allow_None=True, default=None,
                            readonly=True, fget=lambda self : self._channel_D)

    channels = Property(readonly=True, doc='Data of all available channels')

    x_axis = ClassSelector(doc='X-axis data', class_=(numpy.ndarray,), allow_None=True, default=None,
                            readonly=True, fget=lambda self : self._x_axis)
    
    value_range = Tuple(default=(0.7, 1), metadata=dict(unit='V'), length=2, accept_list=True, item_type=(float, int),
                        doc='Value range of the oscilloscope')
    
    @action(input_schema=set_trigger_schema)
    def set_trigger(self, channel : str, enabled : bool, threshold : float, adc : bool = False,
                    direction : str = 'rising', delay : int = 0, auto_trigger : int = 1000) -> None:
        """
        Simulates https://gitlab.com/hololinked-examples/picoscope/-/blame/main/picoscope/pico6000.py?ref_type=heads#L188 

        a function to simulate setting oscilloscope trigger settings with a schema to validate the input arguments
        """
        pass 

    @action()
    def set_trigger_no_schema(self, channel : str, enabled : bool, threshold : float, adc : bool = False,
                    direction : str = 'rising', delay : int = 0, auto_trigger : int = 1000):
        """
        Test set_trigger without schema
        """
        pass 

    def __init__(self, instance_name : str, **kwargs):
        super().__init__(instance_name=instance_name, **kwargs)
        self._run = False
        self._x_axis = None
        self._channel_A = None
        self._channel_B = None
        self._channel_C = None
        self._channel_D = None
        self._thread = None

    @depends_on(time_resolution, time_range, on_init=False)
    def calculate_x_axis(self):
        """recalculate x-axis when time resolution or time range changes"""
        number_of_samples = int(self.time_range / self.time_resolution)
        self._x_axis = numpy.linspace(0, self.time_range, number_of_samples)
        self.logger.info(f"X-axis calculated with {number_of_samples} samples")


    data_ready_event = Event(doc='Event to notify if data is ready', friendly_name='data-ready-event',
                            schema={'type': 'string', 'format': 'date-time'})

    def measure(self, max_count : typing.Optional[int] = None):  
        self._run = True
        number_of_samples = int(self.time_range / self.time_resolution)
        self.calculate_x_axis()
        count = 0
        while self._run:
            if max_count is not None and count >= max_count:
                break
            self._channel_A = ((numpy.random.rand(number_of_samples)*(self.value_range[1] - self.value_range[0])) + self.value_range[0])
            self._channel_B = ((numpy.random.rand(number_of_samples)*(self.value_range[1] - self.value_range[0])) + self.value_range[0])
            self._channel_C = ((numpy.random.rand(number_of_samples)*(self.value_range[1] - self.value_range[0])) + self.value_range[0])
            self._channel_D = ((numpy.random.rand(number_of_samples)*(self.value_range[1] - self.value_range[0])) + self.value_range[0])
            count += 1
            self.data_ready_event.push(datetime.datetime.now().strftime("%H:%M:%S.%f"))
            self.logger.info(f"Data ready {count}")

    @action()
    def start(self, max_count : typing.Optional[int] = None):
        self._thread = threading.Thread(target=self.measure, args=(max_count,))
        self._thread.start()

    @action()
    def stop(self):
        self._run = False
     
    state_machine = StateMachine(
        states=['IDLE', 'RUNNING'],
        initial_state='IDLE',
        IDLE = [start],
        RUNNING = [stop]
    )

    logger_remote_access = True

def start_process_1():
     OscilloscopeSim(
        instance_name='oscilloscope-sim-msgspec-json',
        serializer=JSONSerializer()
    ).run(zmq_protocols='IPC')
     

def start_process_2():
    OscilloscopeSim(
        instance_name='oscilloscope-sim-python-json',
        serializer=PythonBuiltinJSONSerializer()
    ).run(zmq_protocols='IPC')



if __name__ == '__main__':
    # import multiprocessing

    # p1 = multiprocessing.Process(target=start_process_1)
    # p1.start()

    # p2 = multiprocessing.Process(target=start_process_2)
    # p2.start()

    OscilloscopeSim(
        instance_name='oscilloscope-sim',
        serializer='json'
    ).run_with_http_server(port=8080)
