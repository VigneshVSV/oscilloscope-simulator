import typing, numpy, threading, datetime
from hololinked.server import Thing, action, Property, Event, StateMachine 
from hololinked.server import HTTPServer    
from hololinked.param import depends_on
from hololinked.server.properties import Number, ClassSelector, Tuple
from hololinked.server.serializers import JSONSerializer
from hololinked.server.td import JSONSchema
from schema import set_trigger_schema, channel_data_schema



class OscilloscopeSim(Thing):
    """
    Simulates an oscilloscope using numpy's random number generator to generate random voltage values.

    X-axis is time and Y-axis is voltage, with 4 channels available. Set `value_range` to generate simulated
    voltage within the specified range. Adjust time range and time resolution to change the number of samples.    
    """

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

    channels = Property(readonly=True, doc='Data of all available channels', allow_None=True,
                    model=channel_data_schema)

    x_axis = ClassSelector(doc='X-axis/time axis', class_=(numpy.ndarray,), allow_None=True, default=None,
                            readonly=True, fget=lambda self : self._x_axis)
    
    value_range = Tuple(default=(0.7, 1), metadata=dict(unit='V'), length=2, accept_list=True, 
                    item_type=(float, int), doc='Value range of the oscilloscope')
    

    def __init__(self, instance_name : str, **kwargs):
        super().__init__(instance_name=instance_name, **kwargs)
        self._run = False
        self._x_axis = None
        self._channel_A = None
        self._channel_B = None
        self._channel_C = None
        self._channel_D = None
        self._channel_settings = dict()
        self._thread = None
    

    @action(input_schema=set_trigger_schema)
    def set_trigger(self, channel: str, enabled: bool, threshold: float, 
                    direction: str = 'rising', delay: int = 0, auto_trigger: int = 1000) -> None:
        """
        Set oscilloscope trigger settings and use the trigger device's `trigger()` method to send a 
        simulated hardware trigger to the oscilloscope. All settings are written at once,
        individual settings cannot be set without resetting the others.
        Shows usage of a schema to validate the input arguments. 
        """
        self._channel_settings[channel] = {
            'enabled': enabled,
            'threshold': threshold,
            'direction': direction,
            'delay': delay,
            'auto_trigger': auto_trigger
        }
        

    @depends_on(time_resolution, time_range, on_init=False)
    def calculate_x_axis(self):
        """recalculate x-axis when time resolution or time range changes"""
        number_of_samples = int(self.time_range / self.time_resolution)
        self._x_axis = numpy.linspace(0, self.time_range, number_of_samples)
        self.logger.info(f"X-axis calculated with {number_of_samples} samples")


    data_ready_event = Event(doc='Event to notify if data is ready', friendly_name='data-ready-event',
                            schema={'type': 'string', 'format': 'date-time'})

    def measure(self, max_count: typing.Optional[int] = None):  
        self._run = True
        self.calculate_x_axis()
        number_of_samples = int(self.time_range / self.time_resolution)
        
        self.state_machine.set_state('RUNNING')
        count = 0
        while self._run and (max_count is None or count < max_count):
            count += 1
            self._channel_A = ((numpy.random.rand(number_of_samples)*(self.value_range[1] - self.value_range[0])) + self.value_range[0])
            self._channel_B = ((numpy.random.rand(number_of_samples)*(self.value_range[1] - self.value_range[0])) + self.value_range[0])
            self._channel_C = ((numpy.random.rand(number_of_samples)*(self.value_range[1] - self.value_range[0])) + self.value_range[0])
            self._channel_D = ((numpy.random.rand(number_of_samples)*(self.value_range[1] - self.value_range[0])) + self.value_range[0])
            self.data_ready_event.push(datetime.datetime.now().strftime("%H:%M:%S.%f"))
            self.logger.info(f"Data ready {count}")
        self.state_machine.set_state('IDLE')

    @action()
    def start(self, max_count: typing.Optional[int] = None) -> None:
        if self._thread is not None and self._thread.is_alive():
            self.logger.warning('Measure thread is already running')
            return
        assert (isinstance(max_count, int) and max_count > 0) or max_count is None, 'max_count must be an integer greater than 0 or None'
        self._thread = threading.Thread(target=self.measure, args=(max_count,))
        self._thread.start()

    @action()
    def stop(self) -> None:
        self._run = False
     
    state_machine = StateMachine(
        states=['IDLE', 'RUNNING'],
        initial_state='IDLE',
        IDLE = [start],
        RUNNING = [stop]
    )

    logger_remote_access = True


JSONSchema.register_type_replacement(numpy.ndarray, 'array', schema={'type': 'array', 'items': {'type': 'number'}}) 

def start_device():
    OscilloscopeSim(
        instance_name='simulations/oscilloscope',
        serializer=JSONSerializer()
    ).run(zmq_protocols='IPC')

def start_https_server():
    server = HTTPServer(['simulations/oscilloscope'], port=5000)
    server.listen()


if __name__ == '__main__':
    import multiprocessing
    
    p1 = multiprocessing.Process(target=start_device)
    p1.start()

    p2 = multiprocessing.Process(target=start_https_server)
    p2.start()