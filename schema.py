set_trigger_schema = {
    'type': 'object',
    'properties' : {
        'enabled' : { 
            'type': 'boolean', 
            'description': 'Enable or disable the trigger',
        },
        'channel' : { 
            'type': 'string', 
            'description': 'Channel to set the trigger',
            'enum': ['A', 'B', 'C', 'D'] 
            # include both external and aux for 5000 & 6000 series
            # let the device driver will check if the channel is valid for the series
        },
        'threshold' : { 
            'description': 'Threshold value for the trigger',
            'type': 'number', 
            'minimum': 0.1,
            'default': 0.5
        },
        'direction' : { 
            'type': 'string',
            'description': 'Trigger direction', 
            'enum': ['above', 'below', 'rising', 'falling', 'rising_or_falling'], 
            'default': 'rising'
        },
        'delay' : { 
            'type': 'integer',
            'description': 'Delay in microseconds',
            'minimum': 0,
            'default': 0
        },
        'auto_trigger' : { 
            'type': 'integer', 
            'description': 'Auto trigger time in microseconds',
            'minimum': 0,
            'default': 1e7
        }
    }
}

channel_data_schema = {
    'type': 'object', 
    'properties': {
        'A': {
            'type': 'array', 
            'items': {'type': 'number'},
            'description': 'Channel A data' 
        }, 
        'B': {
            'type': 'array', 
            'items': {'type': 'number'},
            'description': 'Channel B data'
        },
        'C': {
            'type': 'array', 
            'items': {'type': 'number'},
            'description': 'Channel C data'
        },
        'D': {
            'type': 'array', 
            'items': {'type': 'number'},
            'description': 'Channel D data'
        }
    }
}

acquisition_start_schema = {
    'type': 'object',
    'properties': {
        'max_count': {
            'oneOf': [{
                    'type': 'integer',
                    'minimum': 1
                },
                {'type': 'null'}
            ],           
            'description': 'Maximum number of measurements to take'
        }
    }
}


set_channel_schema = {
    'type': 'object',
    'properties': {
        'channel': {
            'type': 'string',
            'description': 'Channel to set',
            'enum': ['A', 'B', 'C', 'D']
        },
        'enabled': {
            'type': 'boolean',
            'description': 'Enable or disable the channel',
            'default': True
        },
        'simulation_waveform': {
            'description': 'Waveform to simulate on the channel, phase and frequency are randomized and cannot be controlled',
            'default': 'sine',
            'oneOf': [
                {'type': 'null'},
                {'type': 'string', 'enum': ['sine', 'square', 'triangle', 'sawtooth', 'random' ]}
            ]
        },
    }
}


trigger_channel_schema = {
    'type': 'object',
    'properties': {
        'channel': {
            'type': 'string',
            'description': 'Channel to set the trigger',
            'enum': ['A', 'B', 'C', 'D']
        },
        'voltage' : {
            'type': 'number',
            'description': 'Voltage value for the trigger',
            'unit': 'V',
            'default' : 1,
            'minimum' : 1e-3
        },
        'direction': {
            'type': 'string',
            'description': 'Trigger direction',
            'enum': ['above', 'below', 'rising', 'falling', 'rising_or_falling']
        },
        'delay': {
            'type': 'integer',
            'description': 'Delay in microseconds',
            'minimum': 0, 
            'default': 0
        }
    }
}