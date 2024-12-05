from abc import ABC, abstractmethod

class IModem(ABC):
    @abstractmethod
    def connect(self, connection):
        pass

    @abstractmethod
    def addRxCallback(self, callback):
        pass

    @abstractmethod
    def send(self, dst, src, type, payload, status, dsn):
        pass

    @abstractmethod
    def removeRxCallback(self, cb):
        pass
