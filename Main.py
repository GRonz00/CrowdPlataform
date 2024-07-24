from enum import Enum

from rngs import plantSeeds, selectStream
from rvgs import Normal, Bernoulli, Exponential, Hyperexponential, calculate_p, idfStudent
from EventList import *
from math import sqrt
import matplotlib.pyplot as plt

START = 0.0  # initial (open the door)        */
STOP = 2000000.0  # terminal (close the door) time */
SERVERS = 200  # number of servers   #           */
MEAN_CAPACITY_SERVER = 3000000000
V_CAPACITY_SERVER = 500000000
MAX_CAPACITY_SERVER = MEAN_CAPACITY_SERVER + 2 / 3 * MEAN_CAPACITY_SERVER
MIN_CAPACITY_SERVER = MEAN_CAPACITY_SERVER - 2 / 3 * MAX_CAPACITY_SERVER
INTERARRIVAL_TIMES = 0.1
SERVICE_DEMANDS = 4
N_OPERATION_MEAN = SERVICE_DEMANDS * MEAN_CAPACITY_SERVER
arrivalTemp = START
TIME_MAX_SERVER = 5 * SERVICE_DEMANDS
MEAN_NOT_AVAILABLE_TIME = 50
MEAN_AVAILABLE_TIME = 60 - MEAN_NOT_AVAILABLE_TIME
CV = 1
BATCH_SIZE = 512
N_BATCH = 64
LOC = 0.95


class Event:
    def __init__(self, time, event_type, id_server):
        self.time = time
        self.id_server = id_server  #0 nuovo arrivo altrimenti numero server
        self.event_type = event_type  # 0 arrivo 1 completamento 2 non disponibile 3 disponibile

    def __lt__(self, other):
        return self.time < other.time

    @staticmethod
    def get_arrival():
        selectStream(0)
        return Exponential(INTERARRIVAL_TIMES)

    @staticmethod
    def get_operation_n():
        selectStream(1)
        return Exponential(N_OPERATION_MEAN)

    @staticmethod
    def get_not_available():
        selectStream(2)
        return Hyperexponential(MEAN_AVAILABLE_TIME, calculate_p(CV))

    @staticmethod
    def get_available():
        selectStream(3)
        return Hyperexponential(MEAN_NOT_AVAILABLE_TIME, calculate_p(CV))


class EventType:
    ARRIVAL = 0
    COMPLETION = 1
    NOT_AVAILABLE = 2
    AVAILABLE = 3


class Job:
    def __init__(self, n_operation, arrival_time):
        self.arrival_time = arrival_time
        self.n_operation = n_operation  #questo è un artificio per creare il tempo di completamento
        #io non so la grandezza del job, ma solo la capacità dei server, cosi se vanno in coda 2 so quanto tempo gli manca non sapendo quanti giri fara in coda 2


class Server:
    def __init__(self, id, state, capacity, release_request=False, job=None):
        self.release_request = release_request
        self.job = job
        self.state = state  #0 non disponibile, 1 liber, 2 occupato,
        self.capacity = capacity
        self.id = id

    def get_capacity(self):
        return self.capacity

    def current_job(self, job):
        self.job = job


class Server_state(Enum):
    NOT_AVAILABLE = 0
    NOT_BUSY = 1
    BUSY = 2


def run_job(server, job, current_time, event_list):
    server.state = Server_state.BUSY
    t = job.n_operation / server.capacity  #tempo completamento job
    if t > TIME_MAX_SERVER:
        job.n_operation -= server.capacity * TIME_MAX_SERVER
        event_list.insert(
            Event(current_time + TIME_MAX_SERVER, EventType.COMPLETION, server.id))
    else:
        job.n_operation = 0
        event_list.insert(Event(current_time + t, EventType.COMPLETION, server.id))
    server.current_job(job)


# Esempio d'uso
if __name__ == "__main__":

    server_list = []
    queue1 = []
    queue2 = []
    n_completions = 0
    response_time_mean = 0
    batch_mean = 0
    batch_means = []
    batch_sum = 0
    k = 0
    plantSeeds(123456)
    for i in range(SERVERS):
        server_capacity = Normal(MEAN_CAPACITY_SERVER, V_CAPACITY_SERVER, MIN_CAPACITY_SERVER, MAX_CAPACITY_SERVER)
        j = 0
        while j < len(server_list) and server_list[
            j].get_capacity() > server_capacity:  #ordine decrescente di capacità computazionale
            j += 1
        server_list.insert(j, Server(i + 1, Server_state(Bernoulli(MEAN_AVAILABLE_TIME / 60)),
                                     server_capacity))
    event_list = EventList()
    event_list.insert(Event(0, EventType.ARRIVAL, 0))
    for i in range(SERVERS):
        if server_list[i].state == Server_state.NOT_AVAILABLE:
            event_list.insert(Event(Event.get_available(), EventType.AVAILABLE, i))
        else:
            event_list.insert(Event(Event.get_not_available(), EventType.NOT_AVAILABLE, i))
    # Avanza il tempo e gestisci gli eventi
    current_time = 0
    while not event_list.is_empty() and current_time < STOP:
        event = event_list.pop_next()
        current_time = event.time
        match event.event_type:
            case EventType.ARRIVAL:  #gestisci arrivo
                n_op = Event.get_operation_n()
                job = Job(n_op, current_time)
                if not queue1:  #se la coda 1 è libera
                    busy_servers = True
                    for server in server_list:
                        if server.state == Server_state.NOT_BUSY:  #cerco server libero con capacità maggiore
                            run_job(server, job, current_time, event_list)
                            busy_servers = False
                            break
                    if busy_servers:
                        queue1.append(job)
                else:
                    queue1.append(job)
                event_list.insert(Event(current_time + Event.get_arrival(), EventType.ARRIVAL, 0))
            case EventType.COMPLETION:
                for server in server_list:
                    if server.id == event.id_server:
                        break
                job = server.job
                if job.n_operation == 0:
                    n_completions += 1  #Welford
                    d = current_time - job.arrival_time - response_time_mean
                    response_time_mean += d / n_completions
                    if n_completions % BATCH_SIZE == 0:
                        k += 1
                        d_batch = response_time_mean - batch_mean
                        batch_sum += d_batch * d_batch * (k - 1) / k
                        batch_mean += d_batch / k
                        batch_means.append(batch_mean)
                        print(k, response_time_mean)
                        n_completions = 0
                        response_time_mean = 0
                        if k == 64:
                            stdev = sqrt(batch_sum / k)
                            u = 1 - 0.5 * (1 - LOC)
                            t = idfStudent(k - 1, u)
                            w = t * stdev / sqrt(k - 1)
                            print("con confidenza 95.5 il valore atteso è nel intervallo", batch_mean, "+o- ", w)
                            break




                else:
                    queue2.append(job)
                if server.release_request:
                    server.state = Server_state.NOT_AVAILABLE
                    event_list.insert(Event(current_time + Event.get_available(), EventType.AVAILABLE, server.id))
                else:
                    if queue1:
                        job = queue1.pop(0)
                        run_job(server, job, current_time, event_list)
                    else:
                        if queue2:
                            job = queue2.pop(0)
                            run_job(server, job, current_time, event_list)
                        else:
                            server.state = Server_state.NOT_BUSY
            case EventType.AVAILABLE:
                for server in server_list:
                    if server.id == event.id_server:
                        break
                server.release_request = False
                server.state = Server_state.NOT_BUSY
                if queue1:
                    job = queue1.pop(0)
                    run_job(server, job, current_time, event_list)
                else:
                    if queue2:
                        job = queue2.pop(0)
                        run_job(server, job, current_time, event_list)
                event_list.insert(Event(current_time + Event.get_not_available(), EventType.NOT_AVAILABLE, server.id))
            case EventType.NOT_AVAILABLE:
                for server in server_list:
                    if server.id == event.id_server:
                        break
                if server.state == Server_state.BUSY:
                    server.release_request = True
                else:
                    server.state = Server_state.NOT_AVAILABLE
                    event_list.insert(Event(current_time + Event.get_available(), EventType.AVAILABLE, server.id))
        event_list.advance_time(current_time)
    # Grafico delle medie dei batch
    plt.plot(batch_means, marker='o', linestyle='-', color='b')
    plt.xlabel('Batch Number')
    plt.ylabel('Batch Mean Response Time')
    plt.title('Batch Mean Response Time Over Batches')
    plt.grid(True)
    plt.show()

