import os
import re

from . import path

def get_filepath_from_endname(folder_path, endname, ext=None):
    if ext is not None:
        endn_wit_ext = f'{endname}{ext}'
    else:
        endn_wit_ext = endname
    
    for file in path.listdir(folder_path):
        if file.endswith(endname) or file.endswith(endn_wit_ext):
            return os.path.join(folder_path, file)

def get_filepath_from_channel_name(images_path, channel_name):
    h5_aligned_path = ''
    h5_path = ''
    npz_aligned_path = ''
    img_path = ''
    for file in path.listdir(images_path):
        channelDataPath = os.path.join(images_path, file)
        if file.endswith(f'{channel_name}_aligned.h5'):
            h5_aligned_path = channelDataPath
        elif file.endswith(f'{channel_name}.h5'):
            h5_path = channelDataPath
        elif file.endswith(f'{channel_name}_aligned.npz'):
            npz_aligned_path = channelDataPath
        elif file.endswith(f'{channel_name}.tif') or file.endswith(f'{channel_name}.npz'):
            img_path = channelDataPath
    
    if h5_aligned_path:
        return h5_aligned_path
    elif h5_path:
        return h5_path
    elif npz_aligned_path:
        return npz_aligned_path
    elif img_path:
        return img_path
    else:
        return ''

def _validate_filename(filename: str):
    m = list(re.finditer(r'[A-Za-z0-9_\.\-]+', filename))

    invalid_matches = []
    for i, valid_chars in enumerate(m):
        start_idx, stop_idx = valid_chars.span()
        if i == len(m)-1:
            invalid_chars = filename[stop_idx:]
        else:
            next_valid_chars = m[i+1]
            start_next_idx = next_valid_chars.span()[0]
            invalid_chars = filename[stop_idx:start_next_idx]
        if invalid_chars:
            invalid_matches.append(invalid_chars)
    return set(invalid_matches)

def get_filename_cli(question='Insert a filename', logger_func=print):
    while True:
        filename = input(f'{question} (type "q" to cancel): ')
        if filename.lower() == 'q':
            return
        invalid = _validate_filename(filename)
        if not invalid:
            return filename
        
        logger_func(
            f'[ERROR]: The filename contains invalid charachters: {invalid}'
            'Valid charachters are letters, numbers, underscore, full stop, and hyphen.\n'
        )


