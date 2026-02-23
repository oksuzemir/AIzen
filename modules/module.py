import re
from abc import ABCMeta, abstractmethod

class Module(metaclass=ABCMeta):
    def __init__(self, bot):
        self.bot = bot
        self.on = True

    @property
    @abstractmethod
    def cmds(self):
        pass

    def switch(self, msg):
        pass

    def handler(self, msg):
        if re.findall(re.compile(r'^\/切换'), msg.message):
            self.switch(msg)
            return
        
        if self.on:
            for name, reg in self.cmds.items():
                pattern = re.compile(reg)
                match = re.search(pattern, msg.message)
                if match:
                    msg.groups = match.groups()
                    getattr(self, name)(msg)
                    break
