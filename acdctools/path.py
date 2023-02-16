import os

from natsort import natsorted

def listdir(path):
    return natsorted([
        f for f in os.listdir(path)
        if not f.startswith('.')
        and not f == 'desktop.ini'
    ])

def newfilepath(file_path):
    if not os.path.exists(file_path):
        return file_path

    folder_path = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    filename, ext = os.path.splitext(filename)
    i = 0
    while True:
        new_filename = f'{filename}_{i+1}{ext}'
        new_filepath = os.path.join(folder_path, new_filename)
        if not os.path.exists(new_filepath):
            return new_filepath
        i += 1
