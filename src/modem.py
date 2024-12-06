from ahoi.modem.modem import Modem as AHOIModem
from .i_modem import IModem
class Modem(AHOIModem, IModem):
    """Implémentation réelle de l'interface IModem."""

    def connect(self, connection):
        super().connect(connection)
        print(f"Connected to {connection} (real modem)")

    def send(self, src, dst, type, payload=bytearray(), status=None, dsn=None):
        super().send(src, dst, type, payload, status, dsn)

    def addRxCallback(self, callback):
        super().addRxCallback(callback)

    
    def removeRxCallback(self, cb):
        super().removeRxCallback(cb)

    def getVersion(self):
        return super().getVersion()

    def close(self):
        super().close()
