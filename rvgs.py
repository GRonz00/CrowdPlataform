import math
from rngs import random
from math import exp, log, fabs, sqrt

TINY= 1.0e-10
SQRT2PI= 2.506628274631

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

def LogGamma(a):
    # ========================================================================
    # * LogGamma returns the natural log of the gamma function.
    # * NOTE: use a > 0.0
    # *
    # * The algorithm used to evaluate the natural log of the gamma function is
    # * based on an approximation by C. Lanczos, SIAM J. Numerical Analysis, B,
    # * vol 1, 1964.  The constants have been selected to yield a relative error
    # * which is less than 2.0e-10 for all positive values of the parameter a.
    # * ========================================================================

    s = []
    s.append(76.180091729406 / a)
    s.append(-86.505320327112 / (a + 1.0))
    s.append(24.014098222230 / (a + 2.0))
    s.append(-1.231739516140 / (a + 3.0))
    s.append(0.001208580030 / (a + 4.0))
    s.append(-0.000005363820 / (a + 5.0))
    sum = 1.000000000178

    for i in range(0,6):
        sum += s[i]

    temp = (a - 0.5) * log(a + 4.5) - (a + 4.5) + log(SQRT2PI * sum)
    return (temp)
def LogBeta(a,b):
    # ======================================================================
    # * LogBeta returns the natural log of the beta function.
    # * NOTE: use a > 0.0 and b > 0.0
    # *
    # * The algorithm used to evaluate the natural log of the beta function is
    # * based on a simple equation which relates the gamma and beta functions.
    # *
    return (LogGamma(a) + LogGamma(b) - LogGamma(a + b))

def InBeta(a,b,x):
    # =======================================================================
    # * Evaluates the incomplete beta function.
    # * NOTE: use a > 0.0, b > 0.0 and 0.0 <= x <= 1.0
    # *
    # * The algorithm used to evaluate the incomplete beta function is based on
    # * equation 26.5.8 in the Handbook of Mathematical Functions, Abramowitz
    # * and Stegum (editors).  The absolute error is less than 1e-10 for all x
    # * between 0 and 1.
    # * =======================================================================

    if (x > (a + 1.0) / (a + b + 1.0)): # #/* to accelerate convergence   */
        swap = 1                          ##/* complement x and swap a & b */
        x    = 1.0 - x
        t    = a
        a    = b
        b    = t
    else:                                 ##/* do nothing */
        swap = 0

    if (x > 0):
        factor = exp(a * log(x) + b * log(1.0 - x) - LogBeta(a,b)) / a
    else:
        factor = 0.0

    p = [0.0,1.0, -1]
    q = [1.0,1.0, -1]
    f = p[1] / q[1]
    n = 0

    condition = True

    while (condition==True):                  ##/* recursively generate the continued */
        g = f                           ##/* fraction 'f' until two consecutive */
        n += 1                          ##/* values are small                   */

        if ((n % 2) > 0):
            t = (n - 1) / 2.0
            c = -(a + t) * (a + b + t) * x / ((a + n - 1.0) * (a + n))
        else:
            t = n / 2.0
            c = t * (b - t) * x / ((a + n - 1.0) * (a + n))

        p[2] = (p[1] + c * p[0])
        q[2] = (q[1] + c * q[0])
        if (q[2] != 0.0):               ##/* rescale to avoid overflow */
            p[0] = p[1] / q[2]
            q[0] = q[1] / q[2]
            p[1] = p[2] / q[2]
            q[1] = 1.0
            f    = p[1]


        condition = ((fabs(f - g) >= TINY) or (q[1] != 1.0))
    #endWhile


    if (swap == 1):
        return (1.0 - factor * f)
    else:
        return (factor * f)


def pdfStudent(n, x):
    # ===================================
    # * NOTE: use n >= 1 and x > 0.0
    # * ===================================

    s = -0.5 * (n + 1) * log(1.0 + ((x * x) / float(n)))
    t = -1*LogBeta(0.5, n / 2.0)
    return (exp(s + t) / sqrt(float(n)))


def cdfStudent(n, x):
    # ===================================
    # * NOTE: use n >= 1 and x > 0.0
    # * ===================================

    t = (x * x) / (n + x * x)
    s = InBeta(0.5, n / 2.0, t)
    if (x >= 0.0):
        return (0.5 * (1.0 + s))
    else:
        return (0.5 * (1.0 - s))


def idfStudent(n, u):
    # ===================================
    # * NOTE: use n >= 1 and 0.0 < u < 1.0
    # * ===================================
    t = 0.0
    x = 0.0                       #/* initialize to the mean, then */
    condition = True

    while(condition == True):                #/* use Newton-Raphson iteration */
        t = x
        # print("t is set to "+ t)
        x = t + (u - cdfStudent(n, t)) / pdfStudent(n, t)
        # print("x is set to "+x)
        # print(fabs(x-t))
        condition = (fabs(x - t) >= TINY)

    return (x)


# Esempio d'uso
if __name__ == "__main__":
    # Esempio di utilizzo
    cv = 1  # Coefficiente di variazione
    for i in  range(100):
        p = Exponential(cv)
        print("p =",  p)
