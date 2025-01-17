class ModemTransmissionCalculator:
    def __init__(self, n=4, t=0.00256, s=3, use_hamming=True):
        """
        Initialise les paramètres du modem.

        :param n: Nombre de bits par symbole (par défaut : 4)
        :param t: Durée d'un symbole (en secondes, par défaut : 2.56 ms)
        :param s: Nombre de répétitions par symbole (par défaut : 3)
        :param use_hamming: Si le débit net doit inclure le codage Hamming (par défaut : True)
        """
        self.header_size_bits = 48
        self.n = n
        self.t = t
        self.s = s
        self.use_hamming = use_hamming

    def calculate_gross_rate(self):
        """
        Calcule le débit brut (bits/s).
        """
        return self.n / (self.s * self.t)

    def calculate_net_rate(self):
        """
        Calcule le débit net (bits/s) si le codage Hamming est utilisé.
        """
        gross_rate = self.calculate_gross_rate()
        return gross_rate * 0.5 if self.use_hamming else gross_rate

    def calculate_transmission_time(self, payload_size_bits: int):
        """
        Calcule le temps total nécessaire pour transmettre la charge utile et l'en-tête.
        """
        total_bits = payload_size_bits + self.header_size_bits
        net_rate = self.calculate_net_rate()
        time_in_seconds = total_bits / net_rate
        return int(time_in_seconds * 1e6)

    def __str__(self):
        """
        Représentation textuelle des paramètres et du temps calculé.
        """
        return (f"Modem Parameters:\n"
                f"Header size: {self.header_size_bits} bits\n"
                f"Bits per symbol (N): {self.n}\n"
                f"Symbol duration (T): {self.t} s\n"
                f"Repetitions per symbol (S): {self.s}\n"
                f"Using Hamming: {self.use_hamming}\n"
                f"Total transmission time: {self.calculate_transmission_time():.2f} seconds")