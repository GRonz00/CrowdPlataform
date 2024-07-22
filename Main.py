from enum import Enum
from rngs import plantSeeds, random, selectStream
from rvgs import Normal, Bernoulli, Exponential, Hyperexponential
from EventList import *

START = 0.0  # initial (open the door)        */
STOP = 20000.0  # terminal (close the door) time */
SERVERS = 200  # number of servers              */
arrivalTemp = START
TIME_MAX_SERVER = 480  #tempo massimo 8 min


class Event:
    def __init__(self, time, event_type, id_server):
        self.time = time
        self.id_server = id_server  #0 nuovo arrivo altrimenti numero server
        self.type = event_type  # 0 arrivo 1 completamento 2 non disponibile 3 disponibile

    def __lt__(self, other):
        return self.time < other.time

    @staticmethod
    def get_arrival():
        selectStream(0)
        return Exponential(4)

    @staticmethod
    def get_operation_n():
        selectStream(1)
        return Exponential(12000000000)

    @staticmethod
    def get_not_available():
        selectStream(2)
        return Hyperexponential(20, 0.5)

    @staticmethod
    def get_available():
        selectStream(3)
        return Hyperexponential(40, 0.5)


class EventType:
    ARRIVAL = 0
    COMPLETION = 1
    NOT_AVAILABLE = 2
    AVAILABLE = 3

    """
    def esegui_job:
            if cerca server libero (con capacità maggiore)
            calcola tempo completamento e salvalo nel job (controlla se maggiore 8min)
            aggiorna num operazioni job
            rendi server occupato
            genera evento completamento server
            else aggungi coda 1 se job di coda 1 altrimenti 2 se job coda 2
    def new_arrival(self):
        calcola numero operazioni 
        if ci sono job in coda 1
            aggiungi alla coda 1
        else {
            esgui job}
        genera evento nuovo arrivo
    def competamento(self)
        if n_operazioni job == 0
            metti nella media tempo completamento job
        else job va in coda 2
        if(server_richiesta_rilascio==false)
            metti stato server libero
            if ci sono job in coda 1
                esegui job coda1
                metti stato server occupato
                genera evento server occupato
            else if ci sono job in coda 2
                esegui job coda 2
                metti stato server occupato
                genera evento server occupato
        else
            metti stato server non disponibile
            genera evento server disponibile
            server_richiesta_rilascio==false
    def non_disponibile(,server):
        if stato server == libero
            metti stato server non disponibile
            genera evento server disponibile
        else 
            server_richiesta_rilascio = true
    def disponibile
        metti stato server = libero
        if ci sono job in coda eseguili
    """


class Job:
    def __init__(self, n_operation, queue_time=0, response_time=0):
        self.response_time = response_time
        self.queue_time = queue_time
        self.n_operation = n_operation  #questo è un artificio per creare il tempo di completamento
        #io non so la grandezza del job, ma solo la capacità dei server, cosi se vanno in coda 2 so quanto tempo gli manca non sapendo quanti giri fara in coda 2

    def update_response_time(self, new_time):
        self.response_time = new_time

    def update_queue_time(self, new_time):
        self.queue_time = new_time

    def update_n_operation(self, ope_done):
        self.n_operation -= ope_done
        if self.n_operation < 0:
            self.n_operation = 0


class Server:
    def __init__(self, id, state, capacity, job=None):
        self.job = job
        self.state = state  #0 non disponibile, 1 liber, 2 occupato,
        self.capacity = capacity
        self.id = id

    def current_job(self, job):
        self.job = job


class Server_state(Enum):
    NOT_AVAILABLE = 0
    NOT_BUSY = 1
    BUSY = 2


# Esempio d'uso
if __name__ == "__main__":

    server_list = []
    queue1 = []
    queue2 = []
    n_completions = 0
    response_time_mean = 0
    for i in range(SERVERS):
        server_capacity = Normal(3000000000, 1000000000, 1000000000, 5000000000)
        server_list.append(Server(i + 1, Bernoulli(80), server_capacity))
        j = 0
        while server_list[j].get_capacity() > server_capacity:  #ordine decrescente di capacità computazionale
            j += 1
        server_list.insert(j, Server(i + 1, Bernoulli(80), server_capacity))  #80% possibilita server disponibile
    event_list = EventList()
    event_list.insert(Event(0, EventType.ARRIVAL, 0))
    for i in range(SERVERS):
        if server_list[i].state == Server_state.NOT_AVAILABLE:
            event_list.insert(Event(Event.get_available(), EventType.AVAILABLE, i))
        else:
            event_list.insert(Event(Event.get_not_available(), EventType.NOT_AVAILABLE, i))
    # Avanza il tempo e gestisci gli eventi
    current_time = 0
    while event := event_list.pop_next() & current_time < 20:
        current_time = event.time
        match event.event_type:
            case EventType.ARRIVAL:  #gestisci arrivo
                n_op = Event.get_operation_n()
                job = Job(n_op)
                if not queue1:  #se la coda 1 è libera
                    busy_servers = True
                    for server in server_list:
                        if server.state == Server_state.NOT_BUSY:  #cerco server libero
                            t = job.n_operation / server.capacity  #tempo completamento job
                            if t > TIME_MAX_SERVER:
                                job.update_n_operation(n_op - server.capacity * TIME_MAX_SERVER)
                                job.update_response_time(current_time + TIME_MAX_SERVER)
                                event_list.insert(
                                    Event(current_time + TIME_MAX_SERVER, EventType.COMPLETION, server.id))
                            else:
                                job.update_n_operation(n_op)
                                job.update_response_time(current_time + t)
                                event_list.insert(Event(current_time + t, EventType.COMPLETION, server.id))
                            server.current_job(job)
                            busy_servers = False
                            break
                    if busy_servers:
                        queue1.append(job)
                else:
                    queue1.append(job)
                event_list.insert(Event(current_time+Event.get_arrival(), EventType.ARRIVAL, 0))
            case EventType.COMPLETION:
                for server in server_list:
                    if server.id == event.id_server:
                        break
                job = server.job
                if job.n_operation==0:
                    n_completions+=1
                    d = job.response_time - response_time_mean
                    response_time_mean = response_time_mean + d/n_completions




        event_list.advance_time(current_time)
