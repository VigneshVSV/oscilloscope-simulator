set_trigger_schema = {
    'type': 'object',
    'properties' : {
        'enabled' : { 
            'type': 'boolean' 
        },
        'channel' : { 
            'type': 'string', 
            'enum': ['A', 'B', 'C', 'D', 'EXTERNAL', 'AUX'] 
            # include both external and aux for 5000 & 6000 series
            # let the device driver will check if the channel is valid for the series
        },
        'threshold' : { 
            'type': 'number' 
        },
        'adc' : { 
            'type': 'boolean'
        },
        'direction' : { 
            'type': 'string', 
            'enum': ['above', 'below', 'rising', 'falling', 'rising_or_falling'] 
        },
        'delay' : { 
            'type': 'integer'
        },
        'auto_trigger' : { 
            'type': 'integer', 
            'minimum': 0 
        }
    }
}