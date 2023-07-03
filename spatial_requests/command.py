from enum import Enum

class CommandType(Enum):
    EXECUTE = 1
    REQUEST = 2
    NONE = 3

class Command:

    def __init__(self, type, obj_name=None, new_pos=None, edge=None, request_str=None):
        self.type = type
        self.name = obj_name
        self.new_pos = new_pos
        self.request_str = request_str
        self.edge = edge