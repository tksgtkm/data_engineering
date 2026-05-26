import os
import fnmatch
import gzip
import bz2
import re

def open_gzip(filenames):
    for filename in filenames:
        if filename.endswith('.gz'):
            f = gzip.open(filename, 'rt')
            