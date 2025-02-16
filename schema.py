set_trigger_schema = {
    'type': 'object',
    'properties' : {
        'enabled' : { 
            'type': 'boolean', 
            'description': 'Enable or disable the trigger'
        },
        'channel' : { 
            'type': 'string', 
            'description': 'Channel to set the trigger',
            'enum': ['A', 'B', 'C', 'D', 'EXTERNAL', 'AUX'] 
            # include both external and aux for 5000 & 6000 series
            # let the device driver will check if the channel is valid for the series
        },
        'threshold' : { 
            'description': 'Threshold value for the trigger',
            'type': 'number', 
            'minimum': 0.1
        },
        'direction' : { 
            'type': 'string',
            'description': 'Trigger direction', 
            'enum': ['above', 'below', 'rising', 'falling', 'rising_or_falling'] 
        },
        'delay' : { 
            'type': 'integer',
            'description': 'Delay in microseconds',
            'minimum': 0
        },
        'auto_trigger' : { 
            'type': 'integer', 
            'description': 'Auto trigger time in microseconds',
            'minimum': 0 
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