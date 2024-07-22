import math
from rngs import random
from math import log


def Normal(m, s, lower, upper):
    #========================================================================
    # Returns a normal (Gaussian) distributed real number limited between
    # lower and upper.
    # NOTE: use s > 0.0
    #
    # Uses a very accurate approximation of the normal idf due to Odeh & Evans,
    # J. Applied Statistics, 1974, vol 23, pp 96-97.
    #========================================================================
    #
    p0 = 0.322232431088
    q0 = 0.099348462606
    p1 = 1.0
    q1 = 0.588581570495
    p2 = 0.342242088547
    q2 = 0.531103462366
    p3 = 0.204231210245e-1
    q3 = 0.103537752850
    p4 = 0.453642210148e-4
    q4 = 0.385607006340e-2

    while True:
        u = random()
        if u < 0.5:
            t = math.sqrt(-2.0 * math.log(u))
        else:
            t = math.sqrt(-2.0 * math.log(1.0 - u))

        p = p0 + t * (p1 + t * (p2 + t * (p3 + t * p4)))
        q = q0 + t * (q1 + t * (q2 + t * (q3 + t * q4)))

        if u < 0.5:
            z = (p / q) - t
        else:
            z = t - (p / q)

        result = m + s * z

        # Verifica se il risultato è tra i limiti desiderati
        if lower <= result <= upper:
            return result


def Bernoulli(p):
    #========================================================
    #Returns 1 with probability p or 0 with probability 1 - p.
    #NOTE: use 0.0 < p < 1.0
    #========================================================

    if random() < 1 - p:
        return 0
    else:
        return 1


def Exponential(m):
    #=========================================================
    #Returns an exponentially distributed positive real number.
    #NOTE: use m > 0.0
    #=========================================================
    #
    return (-m * log(1.0 - random()))


def Hyperexponential(m, p):
    if Bernoulli(p) == 1:
        return Exponential(2 * p * m)
    else:
        return Exponential(2 * (1 - p) * m)


def calculate_p(cv):
    if cv < 1:
        raise ValueError("Il CV deve essere maggiore di 1 per una distribuzione iperesponenziale valida")
    return (1 + math.sqrt(1 - (2 / (cv ** 2 + 1)))) / 2


# Esempio d'uso
if __name__ == "__main__":
    # Esempio di utilizzo
    cv = 1.45773797  # Coefficiente di variazione
    p = calculate_p(cv)
    print("p =",  p)
