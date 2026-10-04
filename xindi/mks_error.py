"""Port of src/mks_error.cpp"""

from .cpp import json_dump
from .mks_log import cout


def parse_error(error):
    cout(json_dump(error))
