from abc import ABC, abstractmethod

class IModem(ABC):
    """Interface pour les modems."""
    @abstractmethod
    def connect(self, connection):
        """Enregistre la connexion au modem.
        Args:
           connection: Nom du port série auquel le modem est connecté.
           ou adresse IP et port du modem avec le prefix "tcp@"
        """
        pass

    @abstractmethod
    def receive(self, thread=False):
        """Démarre la réception de paquets.

        Args:
            thread: Si Vrai, mode non-bloquant. Sinon, mode bloquant.
        """

    @abstractmethod
    def addRxCallback(self, callback):
        """Ajoute une fonction à appeler lors de la réception d'un paquet.

        Args:
            callback: Fonction à appeler lors de la réception d'un paquet.
        """
        pass

    @abstractmethod
    def send(self, src, dst, type, payload, status, dsn):
        """Envoie un paquet via le réseau acoustique.

        Args:
            src: Adresse source du modem (0-254).
            dst: Adresse du modem qui doit recevoir le paquet (0-254). ou 255 pour broadcast
            payload: Données à envoyer.
            status: flag de status du paquet.
            dsn: Numéro de séquence du paquet.
        """
        pass

    @abstractmethod
    def removeRxCallback(self, cb):
        """Supprime une fonction à appeler lors de la réception d'un paquet.

        Args:
            cb: Fonction à supprimer.
        """
        pass
