from math import sqrt

import matplotlib.pyplot as plt
from rngs import selectStream, plantSeeds
from rvgs import Exponential, Hyperexponential, calculate_p, Normal, Bernoulli, idfStudent
from EventList import *
from Server import Server, Server_state, ServerStructure

START = 0.0  # initial (open the door)        */
STOP = 2000000.0  # terminal (close the door) time */

SERVERS = 200  # number of servers   #           */
MEAN_CAPACITY_SERVER = 3000000000
V_CAPACITY_SERVER = 500000000
MAX_CAPACITY_SERVER = MEAN_CAPACITY_SERVER + 2 / 3 * MEAN_CAPACITY_SERVER
MIN_CAPACITY_SERVER = MEAN_CAPACITY_SERVER - 2 / 3 * MAX_CAPACITY_SERVER

INTERARRIVAL_TIMES = 0.05
SERVICE_DEMANDS = 6
N_OPERATION_MEAN = SERVICE_DEMANDS * MEAN_CAPACITY_SERVER
arrivalTemp = START

TIME_MAX_SERVER = 3 * SERVICE_DEMANDS

CV = 5

BATCH_SIZE = 1028
N_BATCH = 512
N_REPLICATION = 96
REPLICATION_SIZE = 3000
LOC = 0.95
FINITE_HORIZON = False


class Job:
    def __init__(self, n_operation, arrival_time):
        self.arrival_time = arrival_time
        self.n_operation = n_operation  #questo è un artificio per creare il tempo di completamento
        self.enter_server = arrival_time
        #io non so la grandezza del job, ma solo la capacità dei server, cosi se vanno in coda 2 so quanto tempo gli manca non sapendo quanti giri fara in coda 2


def run_job(server, job, current_time, event_list, server_list):
    server_list.update_state(server.id, Server_state.BUSY)
    t = job.n_operation / server.capacity  #tempo completamento job
    if t > TIME_MAX_SERVER:
        job.n_operation -= server.capacity * TIME_MAX_SERVER
        event_list.insert(
            Event(current_time + TIME_MAX_SERVER, EventType.COMPLETION, server.id))
    else:
        job.n_operation = 0
        event_list.insert(Event(current_time + t, EventType.COMPLETION, server.id))
    server_list.update_job(server.id, job)


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


if __name__ == "__main__":
    batch_means_list = []
    reps_mean_list = []
    mean_not_av = [10, 15, 20, 25, 30]
    for q in mean_not_av:
        global MEAN_NOT_AVAILABLE_TIME
        global MEAN_AVAILABLE_TIME
        MEAN_NOT_AVAILABLE_TIME = q
        MEAN_AVAILABLE_TIME = 60 - q

        server_list = ServerStructure()
        queue1 = []
        queue2 = []
        n_completions = 0
        response_time_mean_single_batch = 0
        batchs_mean = 0
        batch_sum = 0
        x = 0
        reps_mean = 0
        k = 0
        v = 0
        plantSeeds(123456)
        for i in range(SERVERS):
            server_capacity = Normal(MEAN_CAPACITY_SERVER, V_CAPACITY_SERVER, MIN_CAPACITY_SERVER, MAX_CAPACITY_SERVER)
            server_list.add_server(Server(i + 1, Server_state(Bernoulli(MEAN_AVAILABLE_TIME / 60)), server_capacity))
        event_list = EventList()
        event_list.insert(Event(0, EventType.ARRIVAL, 0))
        for i in range(SERVERS):
            if server_list.search_by_id(i + 1).state == Server_state.NOT_AVAILABLE:
                event_list.insert(Event(Event.get_available(), EventType.AVAILABLE, i + 1))
            else:
                event_list.insert(Event(Event.get_not_available(), EventType.NOT_AVAILABLE, i + 1))
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
                        server = server_list.get_server_max_capacity_not_busy()
                        if server:  #se c'è un server libero
                            run_job(server, job, current_time, event_list, server_list)
                        else:
                            queue1.append(job)
                    else:
                        queue1.append(job)
                    event_list.insert(Event(current_time + Event.get_arrival(), EventType.ARRIVAL, 0))
                case EventType.COMPLETION:
                    server = server_list.search_by_id(event.id_server)
                    job = server.job
                    if job.n_operation == 0:
                        n_completions += 1  #Welford
                        if FINITE_HORIZON:
                            d = current_time - job.arrival_time - x
                            x += d / n_completions  #x è la media della singola rep
                            if n_completions % REPLICATION_SIZE == 0:
                                k += 1
                                current_time = 0
                                queue1 = []
                                queue2 = []
                                event_list.clear()
                                event_list.insert(Event(0, EventType.ARRIVAL, 0))
                                server_list_capacity = []
                                for i in range(SERVERS):
                                    server_list_capacity.append(server_list.search_by_id(i + 1).get_capacity())
                                server_list = ServerStructure()
                                for i in range(SERVERS):
                                    state_s = Server_state(Bernoulli(MEAN_AVAILABLE_TIME / 60))
                                    server_list.add_server(Server(i + 1, state_s, server_list_capacity[i]))
                                    if state_s == Server_state.NOT_AVAILABLE:
                                        event_list.insert(Event(Event.get_available(), EventType.AVAILABLE, i + 1))
                                    else:
                                        event_list.insert(
                                            Event(Event.get_not_available(), EventType.NOT_AVAILABLE, i + 1))
                                d_rep = x - reps_mean
                                v += d_rep * d_rep * (k - 1) / k
                                reps_mean += d_rep / k  #è la media delle medie delle rep
                                reps_mean_list.append(reps_mean)
                                #print(k, x)  #questa è la media della singola rep
                                if k == N_REPLICATION:
                                    stdev = sqrt(v / k)
                                    u = 1 - 0.5 * (1 - LOC)
                                    t = idfStudent(k - 1, u)
                                    w = t * stdev / sqrt(k - 1)
                                    print("con confidenza 95.5 il valore atteso è nel intervallo", reps_mean, "+o- ", w)
                                    break
                        else:
                            d = current_time - job.arrival_time - response_time_mean_single_batch
                            response_time_mean_single_batch += d / n_completions
                            if n_completions % BATCH_SIZE == 0:
                                #print("tempo nel server", current_time - job.enter_server)
                                #print("tempo in coda", job.enter_server - job.arrival_time)
                                #print("tempo di risposta", current_time - job.arrival_time)
                                k += 1
                                d_batch = response_time_mean_single_batch - batchs_mean
                                batch_sum += d_batch * d_batch * (k - 1) / k
                                batchs_mean += d_batch / k
                                batch_means_list.append(batchs_mean)
                                with open("batch_mean.txt", "a") as file:
                                    file.write(str(response_time_mean_single_batch) + "\n")
                                #print(k, response_time_mean_single_batch)
                                n_completions = 0
                                response_time_mean_single_batch = 0
                                if k == N_BATCH:
                                    stdev = sqrt(batch_sum / k)
                                    u = 1 - 0.5 * (1 - LOC)
                                    t = idfStudent(k - 1, u)
                                    w = t * stdev / sqrt(k - 1)
                                    print(
                                          "con confidenza 95.5 il valore atteso è nel intervallo", batchs_mean, "+o- ",
                                          w," quando mean unavailability time =", MEAN_NOT_AVAILABLE_TIME)
                                    break
                    else:
                        queue2.append(job)
                    if server.release_request:
                        server_list.update_state(server.id, Server_state.NOT_AVAILABLE)
                        event_list.insert(Event(current_time + Event.get_available(), EventType.AVAILABLE, server.id))
                    else:
                        if queue1:
                            job = queue1.pop(0)
                            job.enter_server = current_time
                            run_job(server, job, current_time, event_list, server_list)
                        else:
                            if queue2:
                                job = queue2.pop(0)
                                run_job(server, job, current_time, event_list, server_list)
                            else:
                                server_list.update_state(server.id, Server_state.NOT_BUSY)
                case EventType.AVAILABLE:
                    server = server_list.search_by_id(event.id_server)
                    server_list.update_release(server.id, False)
                    server_list.update_state(server.id, Server_state.NOT_BUSY)
                    if queue1:
                        job = queue1.pop(0)
                        job.enter_server = current_time
                        run_job(server, job, current_time, event_list, server_list)
                    else:
                        if queue2:
                            job = queue2.pop(0)
                            run_job(server, job, current_time, event_list, server_list)
                    event_list.insert(
                        Event(current_time + Event.get_not_available(), EventType.NOT_AVAILABLE, server.id))
                case EventType.NOT_AVAILABLE:
                    server = server_list.search_by_id(event.id_server)
                    if server.state == Server_state.BUSY:
                        server_list.update_release(server.id, True)
                    else:
                        server_list.update_state(server.id, Server_state.NOT_AVAILABLE)
                        event_list.insert(Event(current_time + Event.get_available(), EventType.AVAILABLE, server.id))
            event_list.advance_time(current_time)
    if FINITE_HORIZON:
        plt.plot(reps_mean_list, marker='o', linestyle='-', color='b')
        plt.xlabel('Rep Number')
        plt.ylabel('Rep Response Time')
        plt.grid(True)
        plt.show()
    else:
        plt.plot(batch_means_list[0:N_BATCH], marker='o', linestyle='-', color='b', markersize=1, label="mean unavailability time = "+str(mean_not_av[0]))
        plt.plot(batch_means_list[N_BATCH + 1:2 * N_BATCH], marker='o', linestyle='-', color='r', markersize=1,
                 label="mean unavailability time = "+str(mean_not_av[1]))
        plt.plot(batch_means_list[2 * N_BATCH + 1:3 * N_BATCH], marker='o', linestyle='-', color='g', markersize=1,
                 label="mean unavailability time = "+str(mean_not_av[2]))
        plt.plot(batch_means_list[3 * N_BATCH + 1:4 * N_BATCH], marker='o', linestyle='-', color='c', markersize=1,
                 label="mean unavailability time = "+str(mean_not_av[3]))
        plt.plot(batch_means_list[4 * N_BATCH + 1:5 * N_BATCH], marker='o', linestyle='-', color='k', markersize=1,
                 label="mean unavailability time = "+str(mean_not_av[4]))
        plt.xlabel('Batch Number')
        plt.ylabel('Response Time')
        plt.title('CV = 1')
        plt.legend()
        plt.grid(True)
        plt.show()
