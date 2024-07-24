from enum import Enum
from sortedcontainers import SortedDict


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


class ServerStructure:  #albero di ricerca misto hash map
    def __init__(self):
        self.hash_table = {}
        self.sorted_dict = SortedDict()

    def add_server(self, server):
        self.hash_table[server.id] = server
        if server.state == Server_state.NOT_BUSY:
            if server.capacity not in self.sorted_dict:
                self.sorted_dict[server.capacity] = []
            self.sorted_dict[server.capacity].append(server)

    def search_by_id(self, id):
        return self.hash_table.get(id, None)

    def get_server_max_capacity_not_busy(self):
        if self.sorted_dict:
            return self.sorted_dict.peekitem(-1)[1][0]
        return None

    def update_state(self, id, new_state):
        server = self.hash_table.get(id, None)
        if server:
            if new_state == Server_state.NOT_BUSY:
                if server.capacity not in self.sorted_dict:
                    self.sorted_dict[server.capacity] = []
                if server not in self.sorted_dict[server.capacity]:
                    self.sorted_dict[server.capacity].append(server)
            else:
                if server.capacity in self.sorted_dict:
                    if server in self.sorted_dict[server.capacity]:
                        self.sorted_dict[server.capacity].remove(server)
                    if not self.sorted_dict[server.capacity]:
                        del self.sorted_dict[server.capacity]
        server.state = new_state
        self.hash_table[id] = server

    def update_release(self, id, release_request):
        server = self.search_by_id(id)
        server.release_request = release_request
        self.hash_table[id] = server

    def update_job(self, id, job):
        server = self.search_by_id(id)
        server.job = job
        self.hash_table[id] = server
