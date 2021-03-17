import asyncio
import os

commandstat_instances = []

path_to_here = os.path.abspath("../")

class CommandRecords:
    
    __slots__ = ["records"]

    def __init__(self):
        self.records = [{}, {}, {}, {}, {}, {}]
        commandstat_instances.append(self)

    def print_record(self, stat="dbconn.py.insert_object", level=0):
        if isinstance(level, int):
            return self.records[level][path_to_here + stat]
        elif level.lower() == 'all':
            return [self.records[i][path_to_here + stat] for i in range(len(self.records))]
        return []
