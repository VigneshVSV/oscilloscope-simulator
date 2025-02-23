import typing, numpy, threading, datetime, os, time, ssl, socket
from pydantic import BaseModel, ConfigDict, Field
from hololinked.param import depends_on
from hololinked.server import Thing, action, Property, Event, StateMachine 
from hololinked.server import HTTPServer    
from hololinked.server.properties import Number, ClassSelector, Tuple
from hololinked.server.serializers import JSONSerializer
from hololinked.server.events import EventDispatcher
from hololinked.server.td import JSONSchema
from schema import (set_trigger_schema, channel_data_schema, acquisition_start_schema, 
                set_channel_schema, trigger_channel_schema)



class Channel(BaseModel):

    class ExecInfo(BaseModel):
        run: bool = False
        thread: threading.Thread = None
        event_dispatcher: EventDispatcher = None
        trigger_event: threading.Event = Field(default_factory=threading.Event)

        model_config = ConfigDict(arbitrary_types_allowed=True)

    class TriggerSettings(BaseModel):
        enabled: bool = False   
        threshold: float = 0
        direction: str = 'rising'
        delay: int = 0
        auto_trigger: int = int(1e7) # 10 seconds

        model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = None
    enabled: bool = True
    data: numpy.ndarray = None
    simulation_waveform: str = 'random'

    exec: ExecInfo = Field(default_factory=ExecInfo)
    trigger_settings: TriggerSettings = Field(default_factory=TriggerSettings)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)





class OscilloscopeSim(Thing):
    """
    Simulates an oscilloscope using numpy's random number generator to generate random voltage values.

    X-axis is time and Y-axis is voltage, with 4 channels available. Set `value_range` to generate simulated
    voltage within the specified range. Adjust time range and time resolution to change the number of samples
    and the gap between measurements to adjust the rate of data and events generated.    
        
    See links section in the TD to access this simulation device with a GUI.
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
    
    JSONSchema.register_type_replacement(numpy.ndarray, 'array', schema={'type': 'array', 'items': {'type': 'number'}}) 

    channels = Property(readonly=True, allow_None=True, model=channel_data_schema,
                        doc='Data of all available channels',
                        fget=lambda self: dict(
                                            A=self._channelA.data, 
                                            B=self._channelB.data, 
                                            C=self._channelC.data, 
                                            D=self._channelD.data
                                        )
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
        self._channelA = Channel(name='A')
        self._channelB = Channel(name='B')
        self._channelC = Channel(name='C')  
        self._channelD = Channel(name='D')
        self._channels = dict(A=self._channelA, B=self._channelB, C=self._channelC, D=self._channelD) # type: typing.Dict[str, Channel]
        self._pollstate_thread = threading.Thread(target=self.poll_state, daemon=True)
        self._pollstate_thread.start()


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
        channel.simulation_waveform = simulation_waveform or 'random'
        

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
            else:
                channel.exec.trigger_event.wait(channel.trigger_settings.auto_trigger*1e-6 if channel.trigger_settings.auto_trigger else None)
                channel.exec.trigger_event.clear()
                time.sleep(channel.trigger_settings.delay*1e-6)
            channel.data = get_waveform(
                                    type=channel.simulation_waveform, 
                                    length=number_of_samples, 
                                    period=numpy.random.randint(1, 20), 
                                    phase=numpy.random.rand()*2*numpy.pi
                                )
            channel.exec.event_dispatcher.push(datetime.datetime.now().strftime("%H:%M:%S.%f"))
            self.logger.info(f"Data ready for {channel.name} - count {count}")
        self.logger.info(f"Measurement for {channel.name} stopped or finished")


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
  

    @action()
    def stop(self) -> None:
        """Stop measurement of all channels"""
        for channel in self._channels.values():
            channel.exec.run = False
            self.logger.info(f"Stopped measurement for {channel.name}")
     

    @action()
    def exit(self):
        """
        overriding exit() from `Thing` parent class which implements a method to exit or stop the server.
        This simulation cannot be exited. This is a dummy method.
        """
        pass 
     
   
    @action(URL_path='/resources/wot-td', http_method="GET")
    def get_thing_description(self, authority = None, ignore_errors = False):
        if authority is None:
            hostname = os.environ.get('hostname', 'localhost')
            if hostname != socket.gethostname() or hostname == 'localhost': # for docker
                authority = f"http{'s' if os.environ.get('ssl_used', False) else ''}://{os.environ.get('hostname', 'localhost')}"            
        td = super().get_thing_description(authority, ignore_errors)
        td['links'] = [
            {
                'href': 'https://thing-control-panel.hololinked.dev/#https://examples.hololinked.dev/simulations/oscilloscope/resources/wot-td',
                'type': 'text/html',
                'rel': 'alternate'
            },
            {
                'href': 'https://github.com/VigneshVSV/hololinked',
                'type': 'text/html',
                'rel': 'external'
            },
            {
                'href': 'https://github.com/VigneshVSV',
                'type': 'text/html',
                'rel': 'external'
            }
        ]
        return td


    @action(input_schema=trigger_channel_schema)
    def external_trigger(self, channel: str, voltage: float, direction: str, delay: int) -> None:
        """
        External trigger method to simulate hardware trigger. This method ideally belongs to a trigger device
        but placed here for simplicity of simulation. 
        """
        threading.Thread(target=self._issue_external_trigger, args=(channel, voltage, direction, delay)).start()

    def _issue_external_trigger(self, channel: str, voltage: float, direction: str, delay: int) -> None:
        channel = self._channels[channel] # type: Channel
        if (channel.trigger_settings.enabled and 
            channel.trigger_settings.threshold <= voltage and 
            channel.trigger_settings.direction == direction
        ):
            time.sleep(delay*1e-6)
            self.logger.info(f"External trigger received for {channel.name}")
            channel.exec.trigger_event.set()
        else:
            self.logger.info(f"External trigger ignored for {channel.name} as conditions do not match")


    state_machine = StateMachine(
        states=['IDLE', 'RUNNING'],
        initial_state='IDLE'
    )

    def poll_state(self):
        """polls the state every half second and sets the state accordingly"""
        while True:
            if (
                any(channel.exec.run for channel in self._channels.values()) or 
                any(channel.exec.thread is not None and channel.exec.thread.is_alive() for channel in self._channels.values())
            ):
                self.state_machine.set_state('RUNNING')
            else: 
                self.state_machine.set_state('IDLE')
            time.sleep(0.5)

    logger_remote_access = True



def get_waveform(type: str, length: int, period: int, phase: float, range: typing.Tuple[int, int] = (0, 1)) -> numpy.ndarray:
    """
    get waveform from type which can be 'sine', 'square', 'triangle', 'sawtooth', 'random' 
    """
    min_val, max_val = range
    if type == 'sine':
        waveform = numpy.sin(numpy.linspace(0, 2 * numpy.pi * period, length) + phase)
    elif type == 'square':
        waveform = numpy.sign(numpy.sin(numpy.linspace(0, 2 * numpy.pi * period, length) + phase))
    elif type == 'triangle':
        waveform = numpy.arcsin(numpy.sin(numpy.linspace(0, 2 * numpy.pi * period, length) + phase))
    elif type == 'sawtooth':
        waveform = 2 * (numpy.linspace(0, period, length) % 1) - 1
        waveform = numpy.roll(waveform, int(phase * length / (2 * numpy.pi)))
    elif type == 'random':
        waveform = numpy.random.rand(length)
    else:
        raise NotImplementedError(f"Waveform type {type} not implemented")
    
    # Scale waveform to the specified range
    waveform = min_val + (max_val - min_val) * (waveform - waveform.min()) / (waveform.max() - waveform.min())
    return waveform
  

def start_device():
    OscilloscopeSim(
        instance_name='simulations/oscilloscope',
        serializer=JSONSerializer()
    ).run(zmq_protocols='IPC')

def start_http_server():
    ssl_context = None
    if os.environ.get('use_ssl', False):
        cert_file = f'assets{os.sep}security{os.sep}certificate.pem'
        key_file = f'assets{os.sep}security{os.sep}key.pem'
        ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_file, keyfile=key_file)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
        os.environ['ssl_used'] = 'True'

    server = HTTPServer(['simulations/oscilloscope'], port=5000, ssl_context=ssl_context)
    server.listen()


if __name__ == '__main__':
    import multiprocessing
    
    p1 = multiprocessing.Process(target=start_device)
    p1.start()

    p2 = multiprocessing.Process(target=start_http_server)
    p2.start()