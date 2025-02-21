import typing, numpy, threading, datetime, os, time, ssl
from pydantic import BaseModel, ConfigDict
from hololinked.param import depends_on
from hololinked.server import Thing, action, Property, Event, StateMachine 
from hololinked.server import HTTPServer    
from hololinked.server.properties import Number, ClassSelector, Tuple
from hololinked.server.serializers import JSONSerializer
from hololinked.server.events import EventDispatcher
from hololinked.server.td import JSONSchema
from schema import set_trigger_schema, channel_data_schema, acquisition_start_schema, set_channel_schema



class Channel(BaseModel):

    class ExecInfo(BaseModel):
        run: bool = False
        thread: threading.Thread = None
        event_dispatcher: EventDispatcher = None

        model_config = ConfigDict(arbitrary_types_allowed=True)

    class TriggerSettings(BaseModel):
        enabled: bool = False   
        threshold: float = 0
        direction: str = 'rising'
        delay: int = 0
        auto_trigger: int = 1000

        model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = None
    enabled: bool = True
    exec: ExecInfo = None
    trigger_settings: TriggerSettings = None
    data: numpy.ndarray = None
    simulation_waveform: str = 'random'
    model_config = ConfigDict(arbitrary_types_allowed=True)




class OscilloscopeSim(Thing):
    """
    Simulates an oscilloscope using numpy's random number generator to generate random voltage values.

    X-axis is time and Y-axis is voltage, with 4 channels available. Set `value_range` to generate simulated
    voltage within the specified range. Adjust time range and time resolution to change the number of samples
    and the gap between measurements to adjust the rate of data and events generated.    
        
    Interact with a GUI here: 
    https://thing-control-panel.hololinked.dev/#https://examples.hololinked.dev/simulations/oscilloscope/resources/wot-td
    """

    time_resolution = Number(default=1e-6, metadata=dict(unit='s'), bounds=(0, None), step=1e-9,
                        doc='Time resolution of the oscilloscope')

    time_range = Number(default=1e-3, metadata=dict(unit='s'), bounds=(0, None), step=1e-9, 
                        doc='Time range of the oscilloscope')
    
    number_of_samples = Number(readonly=True, allow_None=True, default=None,
                                doc='Number of samples in the oscilloscope data (per channel), calculated from time range and time resolution',
                                fget=lambda self: int(self.time_range / self.time_resolution))

    channel_A = ClassSelector(doc='Channel A data', class_=(numpy.ndarray,), 
                            allow_None=True, default=None, readonly=True, 
                            fget=lambda self : self._channelA.data)
   
    channel_B = ClassSelector(doc='Channel B data', class_=(numpy.ndarray,), 
                            allow_None=True, default=None, readonly=True, 
                            fget=lambda self : self._channelB.data)
    
    channel_C = ClassSelector(doc='Channel C data', class_=(numpy.ndarray,), 
                            allow_None=True, default=None, readonly=True, 
                            fget=lambda self : self._channelC.data)

    channel_D = ClassSelector(doc='Channel D data', class_=(numpy.ndarray,), 
                            allow_None=True, default=None, readonly=True, 
                            fget=lambda self : self._channelD.data)

    channels = Property(readonly=True, allow_None=True, model=channel_data_schema,
                        doc='Data of all available channels',
                        fget=lambda self: dict(A=self._channelA.data, B=self._channelB.data, 
                                                C=self._channelC.data, D=self._channelD.data)
                    )

    x_axis = ClassSelector(doc='X-axis/time axis', class_=(numpy.ndarray,), metadata=dict(unit='s'),
                        allow_None=True, default=None, readonly=True, 
                        fget=lambda self : self._x_axis)
    
    value_range = Tuple(default=(0.7, 1), metadata=dict(unit='V'),
                        length=2, accept_list=True, 
                        item_type=(float, int), doc='Value range of the oscilloscope')

    gap_between_measurements = Number(default=1, metadata=dict(unit='s'), bounds=(0, None), step=0.001,
                        doc="""Time gap between measurements, applies to all channels that are not hardware triggered. 
                            Use a comfortable value to prevent excessive data and event generation.""")
    

    def __init__(self, instance_name : str, **kwargs):
        super().__init__(instance_name=instance_name, **kwargs)
        self._x_axis = None
        self._channelA = Channel(name='A',trigger_settings=Channel.TriggerSettings(), exec=Channel.ExecInfo())
        self._channelB = Channel(name='B',trigger_settings=Channel.TriggerSettings(), exec=Channel.ExecInfo())
        self._channelC = Channel(name='C',trigger_settings=Channel.TriggerSettings(), exec=Channel.ExecInfo())  
        self._channelD = Channel(name='D',trigger_settings=Channel.TriggerSettings(), exec=Channel.ExecInfo())
        self._channels = dict(A=self._channelA, B=self._channelB, C=self._channelC, D=self._channelD) # type: typing.Dict[str, Channel]
    

    @action(input_schema=set_trigger_schema)
    def set_trigger(self, channel: str, enabled: bool, threshold: float, 
                    direction: str = 'rising', delay: int = 0, auto_trigger: int = 1000) -> None:
        """
        Set oscilloscope trigger settings and use the trigger device's `trigger()` method to send a 
        simulated hardware trigger to the oscilloscope. All settings are written at once,
        individual settings cannot be set without resetting the others.
        Shows usage of a schema to validate the input arguments. 
        """
        channel = getattr(self, f'_channel{channel}') # type: Channel
        channel.trigger_settings.enabled = enabled
        channel.trigger_settings.threshold = threshold
        channel.trigger_settings.direction = direction
        channel.trigger_settings.delay = delay
        channel.trigger_settings.auto_trigger = auto_trigger

    @action(input_schema=set_channel_schema)
    def set_channel(self, channel: str, enabled: bool, simulation_waveform: typing.Optional[str] = None) -> None:
        """Enable or disable a channel and set the simulation waveform"""
        channel = self._channels[channel] # type: Channel
        channel.enabled = enabled
        channel.simulation_waveform = simulation_waveform
        

    @action()
    def clear_data(self) -> None:
        """Clear data of all channels"""
        for channel in self._channels.values():
            channel.data = None


    @action()
    def reset_device(self) -> None:
        """Reset all settings and clear data of all channels"""
        for channel in self._channels.values():
            channel.enabled = True
            channel.data = None
            channel.trigger_settings = Channel.TriggerSettings()
        self.time_resolution = 1e-6
        self.time_range = 1e-3
        self.value_range = (0.7, 1)
        self.gap_between_measurements = 1

        
    @depends_on(time_resolution, time_range, on_init=False)
    def calculate_x_axis(self):
        """recalculate x-axis when time resolution or time range changes"""
        number_of_samples = int(self.time_range / self.time_resolution)
        self._x_axis = numpy.linspace(0, self.time_range, number_of_samples)
        self.logger.info(f"X-axis calculated with {number_of_samples} samples")

    
    data_ready_event_chA = Event(doc='Event to notify if data is ready for channel A',
                                friendly_name='data-ready-event-channel-A',
                                schema={'type': 'string', 'format': 'date-time'})
    
    data_ready_event_chB = Event(doc='Event to notify if data is ready for channel B', 
                                friendly_name='data-ready-event-channel-B',
                                schema={'type': 'string', 'format': 'date-time'})
    
    data_ready_event_chC = Event(doc='Event to notify if data is ready for channel C', 
                                friendly_name='data-ready-event-channel-C',
                                schema={'type': 'string', 'format': 'date-time'})
    
    data_ready_event_chD = Event(doc='Event to notify if data is ready for channel D', 
                                friendly_name='data-ready-event-channel-D',
                                schema={'type': 'string', 'format': 'date-time'})

    def measure_channel(self, channel: str, max_count: typing.Optional[int] = None):
        channel = self._channels[channel] # type: Channel
        channel.exec.run = True
        if channel.exec.event_dispatcher is None:
            channel.exec.event_dispatcher = getattr(self, f'data_ready_event_ch{channel.name}')
        number_of_samples = int(self.time_range / self.time_resolution)
        count = 0
        while channel.exec.run and (max_count is None or count < max_count):
            count += 1
            if not channel.trigger_settings.enabled:
                time.sleep(self.gap_between_measurements)
                channel.data = ((numpy.random.rand(number_of_samples) * (self.value_range[1] - self.value_range[0])) + self.value_range[0])
                channel.exec.event_dispatcher.push(datetime.datetime.now().strftime("%H:%M:%S.%f"))
               
            self.logger.info(f"Data ready for {channel.name} - count {count}")
        
    @action(input_schema=acquisition_start_schema)
    def start(self, max_count: typing.Optional[int] = None) -> None:
        """
        Start measuring all channels, with optional max_count to limit the number of measurements.
        Channels already capturing data will not be restarted.
        """
        assert (isinstance(max_count, int) and max_count > 0) or max_count is None, 'max_count must be an integer greater than 0 or None'
        for channel in self._channels.values():
            if channel.exec.thread is not None and channel.exec.thread.is_alive():
                self.logger.info(f"Measurement for {channel.name} already running")
                continue
            if not channel.enabled:
                self.logger.info(f"Channel {channel.name} is not enabled, not starting measurement")
                continue
            channel.exec.thread = threading.Thread(target=self.measure_channel, args=(channel.name, max_count))
            channel.exec.thread.start()
            self.logger.info(f"Started measurement for {channel.name}")
        if any(channel.enabled for channel in self._channels.values()):
            self.state_machine.set_state('RUNNING')

    @action()
    def stop(self) -> None:
        """Stop measurement of all channels"""
        for channel in self._channels.values():
            channel.exec.run = False
            self.logger.info(f"Stopped measurement for {channel.name}")
        self.state_machine.set_state('IDLE')

    @action()
    def exit(self):
        """overriding exit() from `Thing` parent class, this simulation cannot be exited. This is a dummy method."""
        pass 
     
    state_machine = StateMachine(
        states=['IDLE', 'RUNNING'],
        initial_state='IDLE',
        IDLE = [start],
        RUNNING = [stop]
    )

    logger_remote_access = True
    
    @action(URL_path='/resources/wot-td', http_method="GET")
    def get_thing_description(self, authority = None, ignore_errors = False):
        if authority is None:
            authority = os.environ.get('hostname', None)
        return super().get_thing_description(authority, ignore_errors)


JSONSchema.register_type_replacement(numpy.ndarray, 'array', schema={'type': 'array', 'items': {'type': 'number'}}) 


def get_waveform(type: str, length: int, period: int, phase: float) -> numpy.ndarray:
    """
    get waveform from type which can be 'sine', 'square', 'triangle', 'sawtooth', 'random' 
    """
    if type == 'sine':
        return numpy.sin(numpy.linspace(0, 2 * numpy.pi * period, length) + phase)
    elif type == 'square':
        return numpy.sign(numpy.sin(numpy.linspace(0, 2 * numpy.pi * period, length) + phase))
    elif type == 'triangle':
        return numpy.arcsin(numpy.sin(numpy.linspace(0, 2 * numpy.pi * period, length) + phase))
    elif type == 'sawtooth':
        return numpy.linspace(-1, 1, length)
    elif type == 'random':
        return numpy.random.rand(length)
    else:
        raise ValueError('Invalid waveform type')

def start_device():
    OscilloscopeSim(
        instance_name='simulations/oscilloscope',
        serializer=JSONSerializer()
    ).run(zmq_protocols='IPC')

def start_https_server():
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(f'assets{os.sep}security{os.sep}certificate.pem',
                        keyfile = f'assets{os.sep}security{os.sep}key.pem')
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3

    server = HTTPServer(['simulations/oscilloscope'], port=5000, ssl_context=ssl_context)
    server.listen()


if __name__ == '__main__':
    import multiprocessing
    
    p1 = multiprocessing.Process(target=start_device)
    p1.start()

    p2 = multiprocessing.Process(target=start_https_server)
    p2.start()