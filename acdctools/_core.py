from typing import Union

from math import log10, floor

time_units_formats = {
    'min': 'minutes', 
    'hour': 'hours', 
    'second': 'seconds', 
    'minutes': 'minutes',
    'seconds': 'seconds', 
    'hours': 'hours', 
    'h': 'hours',
    'd': 'days',
    'm': 'minutes',
    's': 'seconds',
}

time_units_converters = {
    'seconds -> minutes': lambda x: x/60,
    'seconds -> hours': lambda x: x/3600,
    'seconds -> days': lambda x: x/3600/24,
    'minutes -> hours': lambda x: x/60,
    'minutes -> seconds': lambda x: x*60,
    'minutes -> days': lambda x: x/60/24,
    'hours -> minutes': lambda x: x*60,
    'hours -> seconds': lambda x: x*3600,
    'hours -> days': lambda x: x/24,
    'days -> minutes': lambda x: x*24*60,
    'days -> seconds': lambda x: x*24*3600,
    'days -> hours': lambda x: x*24*3600,
}

def round_to_significant(n, n_significant=1):
    return round(n, n_significant-int(floor(log10(abs(n))))-1)

def convert_time_units(x, from_unit, to_unit):
    try:
        from_unit = time_units_formats[from_unit.strip()]
        to_unit = time_units_formats[to_unit.strip()]
        key = f"{from_unit} -> {to_unit}"
        func = time_units_converters[key]
        return func(x)
    except Exception as e:
        return
