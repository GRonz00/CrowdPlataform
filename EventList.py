import heapq


class EventList:
    def __init__(self, threshold=10):
        self.imminent_events = []
        self.future_events = []
        self.threshold = threshold

    def insert(self, event):
        if len(self.imminent_events) < self.threshold or event.time < self.imminent_events[-1].time:
            self._insert_sorted(self.imminent_events, event)
        else:
            heapq.heappush(self.future_events, event)

    def _insert_sorted(self, lst, event):
        index = len(lst)
        lst.append(event)
        while index > 0 and lst[index] < lst[index - 1]:
            lst[index], lst[index - 1] = lst[index - 1], lst[index]
            index -= 1

    def pop_next(self):
        if self.imminent_events:
            return self.imminent_events.pop(0)
        elif self.future_events:
            return heapq.heappop(self.future_events)
        else:
            return None

    def advance_time(self, current_time):
        while self.future_events:
            event = heapq.heappop(self.future_events)
            self._insert_sorted(self.imminent_events, event)

    def is_empty(self):
        if self.imminent_events or self.future_events:
            return False
        else:
            return True

    def clear(self):
        self.imminent_events = []
        self.future_events = []
