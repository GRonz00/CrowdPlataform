from math import sqrt

import matplotlib.pyplot as plt

from EventList import *
from Server import Server, Server_state, ServerStructure
from rngs import selectStream, plantSeeds
from rvgs import Exponential, Hyperexponential, Normal, Bernoulli, idfStudent

START = 0.0
STOP = 2000000.0

SERVERS = 200  # number of servers   #
MEAN_CAPACITY_SERVER = 3000000000
V_CAPACITY_SERVER = 500000000
MAX_CAPACITY_SERVER = MEAN_CAPACITY_SERVER + 2 / 3 * MEAN_CAPACITY_SERVER
MIN_CAPACITY_SERVER = MEAN_CAPACITY_SERVER - 2 / 3 * MAX_CAPACITY_SERVER

MEAN_NOT_AVAILABLE_TIME = 12
MEAN_AVAILABLE_TIME = 48
P = 0.5

INTERARRIVAL_TIMES = 0.05
SERVICE_DEMANDS = 6
N_OPERATION_MEAN = SERVICE_DEMANDS * MEAN_CAPACITY_SERVER

TIME_MAX_SERVER = 2 * SERVICE_DEMANDS

BATCH_SIZE = 1028
N_BATCH =256
N_REPLICATION = 96
REPLICATION_SIZE = 1800
LOC = 0.95
FINITE_HORIZON = False

class Job:
    def __init__(self, n_operation, arrival_time):
        self.arrival_time = arrival_time
        self.n_operation = n_operation  #questo è un artificio per creare il tempo di completamento
        self.enter_server = arrival_time


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
        return Exponential(MEAN_AVAILABLE_TIME)

    @staticmethod
    def get_available():
        selectStream(3)
        return Hyperexponential(MEAN_NOT_AVAILABLE_TIME, P)


class EventType:
    ARRIVAL = 0
    COMPLETION = 1
    NOT_AVAILABLE = 2
    AVAILABLE = 3


def run_simulation(time_list):
    plantSeeds(123456)
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
                        if current_time >= REPLICATION_SIZE:
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
                            x = 0
                            n_completions = 0
                            time_list.append(reps_mean)
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
                            k += 1
                            d_batch = response_time_mean_single_batch - batchs_mean
                            batch_sum += d_batch * d_batch * (k - 1) / k
                            batchs_mean += d_batch / k
                            time_list.append(batchs_mean)
                            #with open("batch_mean.txt", "a") as file:
                                #file.write(str(response_time_mean_single_batch) + "\n")
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
def server_verification():
    global V_CAPACITY_SERVER
    V_CAPACITY_SERVER = 0
    global  MEAN_NOT_AVAILABLE_TIME
    MEAN_NOT_AVAILABLE_TIME = 0
    global  MEAN_AVAILABLE_TIME
    MEAN_AVAILABLE_TIME = 60
    global TIME_MAX_SERVER
    TIME_MAX_SERVER = STOP
    time_list = []
    run_simulation(time_list)
    plt.figure()
    plt.plot(time_list[0:N_BATCH], marker='o', linestyle='-', color='b', markersize=1)
    plt.xlabel('Batch Number')
    plt.ylabel('Response Time')
    plt.title('Test multi server')
    plt.grid(True)
    plt.savefig('test multi server')


def variance_validation():
    mean_not_av = [12,15]
    for q in mean_not_av:
        global MEAN_NOT_AVAILABLE_TIME
        global MEAN_AVAILABLE_TIME
        MEAN_NOT_AVAILABLE_TIME = q
        MEAN_AVAILABLE_TIME = 60 - MEAN_NOT_AVAILABLE_TIME
        p_list = [0.5,0.6,0.7,0.8,0.9]
        time_list = []
        for p in p_list:
            global P
            P = p
            run_simulation(time_list)
        plt.figure()
        plt.plot(time_list[0:N_BATCH], marker='o', linestyle='-', color='b', markersize=1, label="prob = "+str(p_list[0]))
        plt.plot(time_list[N_BATCH:2*N_BATCH], marker='o', linestyle='-', color='g', markersize=1, label="prob = "+str(p_list[1]))
        plt.plot(time_list[2*N_BATCH:3*N_BATCH], marker='o', linestyle='-', color='r', markersize=1, label="prob = "+str(p_list[2]))
        plt.plot(time_list[3*N_BATCH:4*N_BATCH], marker='o', linestyle='-', color='c', markersize=1, label="prob = "+str(p_list[3]))
        plt.plot(time_list[4*N_BATCH:5*N_BATCH], marker='o', linestyle='-', color='m', markersize=1, label="prob = "+str(p_list[4]))
        plt.xlabel('Batch Number')
        plt.ylabel('Response Time')
        plt.title('Validazione varianza')
        plt.legend()
        plt.grid(True)
        plt.savefig('validazione var meanNA= '+str(MEAN_NOT_AVAILABLE_TIME))

def n_server_validation():
    global SERVERS
    n_ser = [100,200,400]
    time_list = []
    for q in n_ser:
        SERVERS = q
        run_simulation(time_list)
    plt.figure()
    plt.plot(time_list[0:N_BATCH], marker='o', linestyle='-', color='b', markersize=1, label="n_server = "+str(n_ser[0]))
    plt.plot(time_list[N_BATCH:2*N_BATCH], marker='o', linestyle='-', color='g', markersize=1, label="n_server = "+str(n_ser[1]))
    plt.plot(time_list[2*N_BATCH:3*N_BATCH], marker='o', linestyle='-', color='r', markersize=1, label="n_server = "+str(n_ser[2]))
    plt.xlabel('Batch Number')
    plt.ylabel('Response Time')
    plt.title('Validazione server')
    plt.yscale('log')
    plt.legend()
    plt.grid(True)
    plt.savefig('validazione server')

def arrival_validation():
    global  INTERARRIVAL_TIMES
    time_list = []
    arr_list = [0.25,0.1,0.05]
    for q in arr_list:
        INTERARRIVAL_TIMES = q
        run_simulation(time_list)
    plt.figure()
    plt.plot(time_list[0:N_BATCH], marker='o', linestyle='-', color='b', markersize=1, label="INTERARRIVAL_TIMES = "+str(arr_list[0]))
    plt.plot(time_list[N_BATCH:2*N_BATCH], marker='o', linestyle='-', color='g', markersize=1, label="INTERARRIVAL_TIMES = "+str(arr_list[1]))
    plt.plot(time_list[2*N_BATCH:3*N_BATCH], marker='o', linestyle='-', color='r', markersize=1, label="INTERARRIVAL_TIMES = "+str(arr_list[2]))
    plt.xlabel('Batch Number')
    plt.ylabel('Response Time')
    plt.title('Validazione tempo di arrivo')
    plt.legend()
    plt.grid(True)
    plt.savefig('validazione arrivi')
def finite_horizont():
    global FINITE_HORIZON
    FINITE_HORIZON = True
    mean_not_av = [6, 9,12,15,18]
    p_list = [0.5,0.6,0.7,0.8,0.9]
    for p in p_list:
        global P
        P = p
        time_list=[]
        for q in mean_not_av:
            global MEAN_NOT_AVAILABLE_TIME
            global MEAN_AVAILABLE_TIME
            MEAN_NOT_AVAILABLE_TIME = q
            MEAN_AVAILABLE_TIME = 60 - MEAN_NOT_AVAILABLE_TIME
            run_simulation(time_list)
        plt.figure()
        plt.plot(time_list[0:N_REPLICATION], marker='o', linestyle='-', color='b', markersize=1, label="mean unavailability time = "+str(mean_not_av[0]))
        plt.plot(time_list[N_REPLICATION:2*N_REPLICATION], marker='o', linestyle='-', color='g', markersize=1, label="mean unavailability time = "+str(mean_not_av[1]))
        plt.plot(time_list[2*N_REPLICATION:3*N_REPLICATION], marker='o', linestyle='-', color='r', markersize=1, label="mean unavailability time = "+str(mean_not_av[2]))
        plt.plot(time_list[3*N_REPLICATION:4*N_REPLICATION], marker='o', linestyle='-', color='c', markersize=1, label="mean unavailability time = "+str(mean_not_av[3]))
        plt.plot(time_list[4*N_REPLICATION:5*N_REPLICATION], marker='o', linestyle='-', color='m', markersize=1, label="mean unavailability time = "+str(mean_not_av[4]))
        plt.xlabel('Rep Number')
        plt.ylabel('Response Time')
        plt.title('Prob = '+str(p))
        plt.legend()
        plt.grid(True)
        save_p = str(p*10)
        plt.savefig('oriz_finito='+save_p[:1])
def infinite_horizon():
    mean_not_av = [6, 9,12,15,18]
    p_list = [0.5,0.6,0.7,0.8,0.9]
    for p in p_list:
        global P
        P = p
        time_list=[]
        for q in mean_not_av:
            global MEAN_NOT_AVAILABLE_TIME
            global MEAN_AVAILABLE_TIME
            MEAN_NOT_AVAILABLE_TIME = q
            MEAN_AVAILABLE_TIME = 60 - MEAN_NOT_AVAILABLE_TIME
            run_simulation(time_list)
        plt.figure()
        #if pl>7:
        #   plt.ylim([4.7, 7.5])
        plt.plot(time_list[0:N_BATCH], marker='o', linestyle='-', color='b', markersize=1, label="prob = "+str(p_list[0]))
        plt.plot(time_list[N_BATCH:2*N_BATCH], marker='o', linestyle='-', color='g', markersize=1, label="prob = "+str(p_list[1]))
        plt.plot(time_list[2*N_BATCH:3*N_BATCH], marker='o', linestyle='-', color='r', markersize=1, label="prob = "+str(p_list[2]))
        plt.plot(time_list[3*N_BATCH:4*N_BATCH], marker='o', linestyle='-', color='c', markersize=1, label="prob = "+str(p_list[3]))
        plt.plot(time_list[4*N_BATCH:5*N_BATCH], marker='o', linestyle='-', color='m', markersize=1, label="prob = "+str(p_list[4]))
        plt.xlabel('Batch Number')
        plt.ylabel('Response Time')
        plt.title('Prob = '+str(p))
        plt.legend()
        plt.grid(True)
        plt.savefig('infinito_prob= '+ str(p*10)[:1])
def increase_arrivals():
    arr_list = [0.0476190476,0.0454545455,0.0434782609,0.041666667]
    inc = 0
    for a in arr_list:
        inc += 5
        global INTERARRIVAL_TIMES
        INTERARRIVAL_TIMES = a
        mean_not_av = [12,15,18]
        for q in mean_not_av:
            time_list = []
            global MEAN_NOT_AVAILABLE_TIME
            global MEAN_AVAILABLE_TIME
            MEAN_NOT_AVAILABLE_TIME = q
            MEAN_AVAILABLE_TIME = 60 - MEAN_NOT_AVAILABLE_TIME
            p_list = [0.5,0.6,0.7,0.8,0.9]
            for p in p_list:
                global P
                P = p
                run_simulation(time_list)
            plt.figure()
            plt.plot(time_list[0:N_BATCH], marker='o', linestyle='-', color='b', markersize=1, label="prob = "+str(p_list[0]))
            plt.plot(time_list[N_BATCH:2*N_BATCH], marker='o', linestyle='-', color='g', markersize=1, label="prob = "+str(p_list[1]))
            plt.plot(time_list[2*N_BATCH:3*N_BATCH], marker='o', linestyle='-', color='r', markersize=1, label="prob = "+str(p_list[2]))
            plt.plot(time_list[3*N_BATCH:4*N_BATCH], marker='o', linestyle='-', color='c', markersize=1, label="prob = "+str(p_list[3]))
            plt.plot(time_list[4*N_BATCH:5*N_BATCH], marker='o', linestyle='-', color='m', markersize=1, label="prob = "+str(p_list[4]))
            plt.xlabel('Batch Number')
            plt.ylabel('Response Time')
            plt.title('arrivals +' +str(inc)+'%'+ 'MNAT='+str(MEAN_NOT_AVAILABLE_TIME)+'s')
            plt.legend()
            plt.grid(True)
            plt.savefig('arrivals +' +str(inc)+'MNAT='+str(MEAN_NOT_AVAILABLE_TIME))

if __name__ == "__main__":
    choice = 0
    while choice != 8:
        print('1) verifica funzionamento multiserver')
        print('2) valida il sistema rispetto al numero di server')
        print('3) valida il sistema rispetto alla varianza')
        print('4) valida il sistema rispetto alla frequenza degli arrivi')
        print('5) analisi del transitorio rispetto varianza e tempo indisponibilità server')
        print('6) analisi della stazionarietà rispetto varianza e tempo indisponibilità server ')
        print('7) analisi della stazionarietà rispetto incremento degli arrivi')
        print('8) fine')
        print('seleziona scelta:')
        try:
            choice = int(input())
        except ValueError:
            choice = 9
        match choice:
            case 1:
                server_verification()
            case 2:
                n_server_validation()
            case 3:
                variance_validation()
            case 4:
                arrival_validation()
            case 5:
                finite_horizont()
            case 6:
                infinite_horizon()
            case 7:
                increase_arrivals()
            case 8:
                break
            case _:
                print('inserire un intero tra 1 e 8')









