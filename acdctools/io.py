import os

from . import path

def get_filepath_from_channel_name(images_path, channel_name):
    h5_aligned_path = ''
    h5_path = ''
    npz_aligned_path = ''
    tif_path = ''
    for file in path.listdir(images_path):
        channelDataPath = os.path.join(images_path, file)
        if file.endswith(f'{channel_name}_aligned.h5'):
            h5_aligned_path = channelDataPath
        elif file.endswith(f'{channel_name}.h5'):
            h5_path = channelDataPath
        elif file.endswith(f'{channel_name}_aligned.npz'):
            npz_aligned_path = channelDataPath
        elif file.endswith(f'{channel_name}.tif'):
            tif_path = channelDataPath
    
    if h5_aligned_path:
        return h5_aligned_path
    elif h5_path:
        return h5_path
    elif npz_aligned_path:
        return npz_aligned_path
    elif tif_path:
        return tif_path
    else:
        return ''