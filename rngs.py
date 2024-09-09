from time import time

#global consts
MODULUS = 2147483647 #/* DON'T CHANGE THIS VALUE                  */
MULTIPLIER = 48271      #/* DON'T CHANGE THIS VALUE                  */
CHECK = 399268537  #/* DON'T CHANGE THIS VALUE                  */
STREAMS = 256        #/* # of streams, DON'T CHANGE THIS VALUE    */
A256 = 22925      #/* jump multiplier, DON'T CHANGE THIS VALUE */
DEFAULT = 123456789  #/* initial seed, use 0 < DEFAULT < MODULUS  */

#statics
stream = 0
initialized = 0
seed = [DEFAULT]
for i in range(1,STREAMS):
    seed.append(DEFAULT)


def random():
    #/* ---------------------------------------------------------------------
    #* Random is a Lehmer generator that returns a pseudo-random real number
    #* uniformly distributed between 0.0 and 1.0.  The period is (m - 1)
    #* where m = 2,147,483,647 amd the smallest and largest possible values
    #* are (1 / m) and 1 - (1 / m) respectively.
    #* ---------------------------------------------------------------------
    #*/
    global seed

    Q = int(MODULUS / MULTIPLIER)
    R = int(MODULUS % MULTIPLIER)

    t = int(MULTIPLIER * (seed[stream] % Q) - R * int(seed[stream] / Q))
    if (t > 0):
        seed[stream] = int(t)
    else:
        seed[stream] = int(t + MODULUS)

    return float(seed[stream] / MODULUS)

def plantSeeds(x):
    # /* --------------------------------------------------------------------
    #  * Use this function to set the state of all the random number generator
    #  * streams by "planting" a sequence of states (seeds), one per stream,
    #  * with all states dictated by the state of the default stream.
    #  * The sequence of planted states is separated one from the next by
    #  * 8,367,782 calls to Random().
    #  * ---------------------------------------------------------------------
    #  */
    global initialized
    global stream
    global seed

    Q = int(MODULUS / A256)
    R = int(MODULUS % A256)

    initialized = 1
    s = stream                             #/* remember the current stream */
    selectStream(0)                        #/* change to stream 0          */
    putSeed(x)                             #/* set seed[0]                 */
    stream = s                             #/* reset the current stream    */
    for j in range(1,STREAMS):
        x = int(A256 * (seed[j - 1] % Q) - R * int((seed[j - 1] / Q)))
        if (x > 0):
            seed[j] = x
        else:
            seed[j] = x + MODULUS


def putSeed(x):
    # /* -------------------------------------------------------------------
    #  * Use this (optional) procedure to initialize or reset the state of
    #  * the random number generator according to the following conventions:
    #  *    if x > 0 then x is the initial seed (unless too large)
    #  *    if x < 0 then the initial seed is obtained from the system clock
    #  *    if x = 0 then the initial seed is to be supplied interactively
    #  * --------------------------------------------------------------------
    #  */
    global seed

    ok = False

    if (x > 0):
        x = x % MODULUS
        # correct if x is too large
    if (x < 0):
        x = time()
        x = x % MODULUS

    if (x == 0):
        while (ok == False):
            line = input("\nEnter a positive integer seed (9 digits or less) >> ")
            x = int(line)
            ok = (0 < x) and (x < MODULUS)
            if (ok == False):
                print("\nInput out of range ... try again\n")


    seed[stream] = int(x)


def getSeed():
    # /* --------------------------------------------------------------------
    #  * Use this (optional) procedure to get the current state of the random
    #  * number generator.
    #  * --------------------------------------------------------------------
    #  */
    return seed[stream]


def selectStream(index):
    #/* ------------------------------------------------------------------
    #* Use this function to set the current random number generator
    #* stream -- that stream from which the next random number will come.
    #* ------------------------------------------------------------------
    #*/
    global stream

    stream = index % STREAMS
    if (initialized == 0) and (stream != 0):   #/* protect against        */
        plantSeeds(DEFAULT)                     #/* un-initialized streams */
