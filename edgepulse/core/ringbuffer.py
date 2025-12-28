from collections import deque

class RingBuffer:
    def __init__(self, maxlen: int):
        self.buf = deque(maxlen=maxlen)

    def append(self, x: float):
        self.buf.append(float(x))

    def values(self):
        return list(self.buf)

    def __len__(self):
        return len(self.buf)
