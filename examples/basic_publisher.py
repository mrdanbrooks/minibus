#!/usr/bin/env python
from minibus import MiniBusSocketClient
import time

class BasicPublisher(MiniBusSocketClient):
    def __init__(self):
        MiniBusSocketClient.__init__(self, name="BasicSocketPublisher")
        self.pub = self.publisher("/chatter", {"type": "string"})

    def run(self):
        try:
            while True:
                self.pub("wub")
                time.sleep(1)
        except KeyboardInterrupt:
            self.close()

if __name__ == "__main__":
    publisher = BasicPublisher()
    publisher.run()
