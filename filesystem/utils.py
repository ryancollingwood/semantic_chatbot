import os
import errno


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def file_exists(path):
    return os.path.exists(path)