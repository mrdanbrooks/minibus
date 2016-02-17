"""
run using
    trial test_bus
or on a mac
    trial-2.7 test_bus
"""
import os
import time
from minibus import MiniBusClient, RemoteServiceException
from minibus2 import MiniBusTwistedClient
from twisted.trial import unittest
from twisted.internet import reactor, defer, task
import jsonschema
 


class BasicPublisher(MiniBusTwistedClient):
    def __init__(self, topic, schema=None):
        MiniBusTwistedClient.__init__(self)
        self.topic = topic
        self.schema = schema or {}
        self.pub = None
        self.running = False
        self._callid = None
        self.counter = 0

    def run(self):
        self.running = True
        self.pub = self.publisher(self.topic, self.schema)
        self._callid = reactor.callLater(0, self.push) 

    def push(self):
        self.pub(self.counter)
#         print "\n%s sent %d" % (self.topic, self.counter)
        if self.running:
            self._callid = reactor.callLater(0.1, self.push) 
            self.counter += 1
        else:
            self._callid = None

    def fini(self):
        if self.running:
            self.running = False
        if self._callid:
            self._callid.cancel()


class BasicSubscriber(MiniBusTwistedClient):
    def __init__(self, topic, schema=None):
        MiniBusTwistedClient.__init__(self)
        self.counter = 0
        self.topic = topic
        self.schema = schema or {}

    def run(self):
        self.subscribe(self.topic, self.schema, self.receive)

    def receive(self, data):
        self.counter += 1
#         print "%s received %s" % (self.topic, data)

    def fini(self):
        pass
        
class TestPubSubBasic(unittest.TestCase):
    """ Test single publisher sending messages to single subscriber.
    The number of messages sent should equal the number received.
    """
    def setUp(self):
        self.subscriber = BasicSubscriber("test")
        self.publisher = BasicPublisher("test")

    def tearDown(self):
        # This, along with code in minibus._cleanup(),  was found via trail 
        # and error using suggestions from http://blackjml.livejournal.com/23029.html
        s1 = self.subscriber._cleanup()
        p1 = self.publisher._cleanup()
        return defer.gatherResults([s1, p1])

    def examin(self):
        self.publisher.fini()
        self.subscriber.fini()
#         print "sent=", self.publisher.counter
#         print "received=", self.subscriber.counter
        self.assertEqual(self.publisher.counter, self.subscriber.counter)

    def test_test(self):
        d = task.deferLater(reactor, 0.5, self.examin)
        return d

class TestMultipleSeperateTopics(unittest.TestCase):
    """ Test two sets of publisher and subscriber pairs talking on different topics.
    There should not be any cross talk.
    """
    def setUp(self):
        self.subscriber1 = BasicSubscriber("test1")
        self.publisher1 = BasicPublisher("test1")
        self.subscriber2 = BasicSubscriber("test2")
        self.publisher2 = BasicPublisher("test2")

    def tearDown(self):
        a = self.subscriber1._cleanup()
        b = self.publisher1._cleanup()
        c = self.subscriber2._cleanup()
        d = self.publisher2._cleanup()
        return defer.gatherResults([a, b, c, d])

    def examin(self):
        self.publisher1.fini()
        self.publisher2.fini()
        self.subscriber1.fini()
        self.subscriber2.fini()
        self.assertEqual(self.publisher1.counter,self.subscriber1.counter)
        self.assertEqual(self.publisher2.counter,self.subscriber2.counter)

    def test_test(self):
        d = task.deferLater(reactor, 0.5, self.examin)
        return d


class TestMultipleSubscribersToTopic(unittest.TestCase):
    """ Tests a single publisher sending to multiple subscribers.
    Each subscriber should hear exactly the same set of messages.
    """
    def setUp(self):
        self.subscriber1 = BasicSubscriber("test")
        self.subscriber2 = BasicSubscriber("test")
        self.subscriber3 = BasicSubscriber("test")
        self.publisher = BasicPublisher("test")

    def tearDown(self):
        a = self.subscriber1._cleanup()
        b = self.subscriber2._cleanup()
        c = self.subscriber3._cleanup()
        d = self.publisher._cleanup()
        return defer.gatherResults([a, b, c, d])

    def examin(self):
        self.publisher.fini()
        self.subscriber1.fini()
        self.subscriber2.fini()
        self.subscriber3.fini()
#         print "sent=", self.publisher.counter
#         print "received=", self.subscriber1.counter
#         print "received=", self.subscriber2.counter
#         print "received=", self.subscriber3.counter
        self.assertEqual(self.publisher.counter,self.subscriber1.counter)
        self.assertEqual(self.publisher.counter,self.subscriber2.counter)
        self.assertEqual(self.publisher.counter,self.subscriber3.counter)

    def test_test(self):
        d = task.deferLater(reactor, 0.5, self.examin)
        return d


class TestMultiplePublishersToTopic(unittest.TestCase):
    """ Tests multiple publishers sending to a single subscriber.
    The subscriber should hear from all the publishers.
    """
    def setUp(self):
        self.subscriber = BasicSubscriber("test")
        self.publisher1 = BasicPublisher("test")
        self.publisher2 = BasicPublisher("test")
        self.publisher3 = BasicPublisher("test")

    def tearDown(self):
        a = self.subscriber._cleanup()
        b = self.publisher1._cleanup()
        c = self.publisher2._cleanup()
        d = self.publisher3._cleanup()
        return defer.gatherResults([a, b, c, d])

    def examin(self):
        self.publisher1.fini()
        self.publisher2.fini()
        self.publisher3.fini()
        self.subscriber.fini()
#         print "sent=", self.publisher1.counter
#         print "sent=", self.publisher2.counter
#         print "sent=", self.publisher3.counter
#         print "received=", self.subscriber.counter
        total_sent = self.publisher1.counter + self.publisher2.counter + self.publisher3.counter
        total_recv = self.subscriber.counter
        self.assertEqual(total_sent,total_recv)

    def test_test(self):
        d = task.deferLater(reactor, 0.5, self.examin)
        return d


class TestMixedTopics(unittest.TestCase):
    """ Test that the regular expressions which define topic names are working
    correctly to route data. """
    def setUp(self):
        self.pub1 = BasicPublisher("foo1")
        self.pub2 = BasicPublisher("foo2")
        self.pub3 = BasicPublisher("bar1")

        self.sub1 = BasicSubscriber(".*1")
        self.sub2 = BasicSubscriber("foo.")
        self.sub3 = BasicSubscriber("foo2")
        self.sub4 = BasicSubscriber("bar")

    def tearDown(self):
        self.pub1._cleanup()
        self.pub2._cleanup()
        self.pub3._cleanup()
        self.sub1._cleanup()
        self.sub2._cleanup()
        self.sub3._cleanup()
        self.sub4._cleanup()

    def test_test(self):
        def deferred_test():
            self.pub1.fini()
            self.pub2.fini()
            self.pub3.fini()
            self.assertEqual(self.pub1.counter + self.pub3.counter, self.sub1.counter)
            self.assertEqual(self.pub1.counter + self.pub2.counter, self.sub2.counter)
            self.assertEqual(self.pub2.counter, self.sub3.counter)
            self.assertEqual(0, self.sub4.counter)
        return task.deferLater(reactor, 0.5, deferred_test)


class TestSchema(unittest.TestCase):
    """ Tests multiple publishers sending to a single subscriber.
    The subscriber should hear from all the publishers.
    """
    def setUp(self):
        self.client = MiniBusTwistedClient()
        self.pub = self.client.publisher("test", {"type": "string"})
        self.client.subscribe("test", {"type": "string"}, self.callback)
        self.count = 0

    def tearDown(self):
        a = self.client._cleanup()
        return defer.gatherResults([a])

    def callback(self, data):
        self.count += 1

    def test_good_schema(self):
        def deferred_good_schema():
            self.pub("this is a test")
        d = task.deferLater(reactor, 0.5, deferred_good_schema)
        return d

    def test_good_schema_callback(self):
        def deferred_good_callback():
            if not self.count == 1:
                raise Exception("bad count")
        def deferred_good_callback_pub():
            self.pub("this is a test")
        d1 = task.deferLater(reactor, 0.5, deferred_good_callback_pub)
        d = task.deferLater(reactor, 1, deferred_good_callback)
        return d

    def test_bad_schema(self):
        def deferred_bad_schema():
            try:
                self.pub({"one": 1, "two": 2})
            except Exception:
                return
            raise Exception("I should not have passed")


        d = task.deferLater(reactor, 0.5, deferred_bad_schema)
        return d

    def test_conflict_schema(self):
        try: 
            self.client.subscribe("test", {"type": "number"}, self.callback)
        except Exception:
            return
        raise Exception("I should not have passed")

class Service1Test(unittest.TestCase):
    def add_two_ints(self, data):
        return sum(data)

    def setUp(self):
        self.srvreq = {'type': 'array' }
        self.srvrply = { 'type': 'integer' }
        self.node1 = MiniBusTwistedClient()
        self.node1.service("add_two_ints", self.srvreq, self.srvrply, self.add_two_ints)
        self.node2 = MiniBusTwistedClient()

    def tearDown(self):
        a = self.node1._cleanup()
        b = self.node2._cleanup()

    @MiniBusTwistedClient.inlineServiceCallbacks
    def test_call(self):
        adder = self.node2.service_client("add_two_ints", self.srvreq, self.srvrply)
        ret = yield task.deferLater(reactor, 0.5, adder, [4,5,6])
        self.assertEqual(ret, 15)

    @MiniBusTwistedClient.inlineServiceCallbacks
    def test_bad_input_call(self):
        adder = self.node2.service_client("add_two_ints", self.srvreq, self.srvrply)
        try:
            ret = yield task.deferLater(reactor, 0.5, adder, 4)
            raise Exception("I should have failed due to not being passed an array")
        except jsonschema.exceptions.ValidationError:
            pass

    @MiniBusTwistedClient.inlineServiceCallbacks
    def test_bad_output_call(self):
        adder = self.node2.service_client("add_two_ints", self.srvreq, {'type': 'string'})
        try:
            ret = yield task.deferLater(reactor, 0.5, adder, [4,5,6])
            raise Exception("I should have failed due to being returned a number instead of a string")
        except jsonschema.exceptions.ValidationError:
            pass

    @MiniBusTwistedClient.inlineServiceCallbacks
    def test_bad_input_data(self):
        adder = self.node2.service_client("add_two_ints", self.srvreq, self.srvrply)
        try:
            ret = yield task.deferLater(reactor, 0.5, adder, [4,'5',6])
            raise Exception("I should have thrown a RemoteServiceException")
        except RemoteServiceException:
            pass


class TestMultiService(unittest.TestCase):
    def add_ints(self, data):
        return sum(data)

    def double_ints(self, data):
        return [x*2 for x in data]

    def print_ints(self, data):
        return " ".join(data)

    def setUp(self):
        self.srvreq = {'type': 'array' }
        self.srvrply = { 'type': 'integer' }
        self.server1 = MiniBusTwistedClient()
        self.server1.service("add_ints", {'type': 'array'}, {'type': 'integer'}, self.add_ints)
        self.server1.service("double_ints", {'type': 'array'}, {'type': 'array'}, self.double_ints)

        self.server2 = MiniBusTwistedClient()
        self.server2.service("print_ints", {'type': 'array'}, {'type': 'string'}, self.print_ints)

        self.client1 = MiniBusTwistedClient()
        self.client2 = MiniBusTwistedClient()

    def tearDown(self):
        a = self.server1._cleanup()
        b = self.server2._cleanup()
        c = self.client1._cleanup()
        d = self.client2._cleanup()

    @MiniBusTwistedClient.inlineServiceCallbacks
    def test_calls(self):
        adder = self.client1.service_client("add_ints", {'type': 'array'}, {'type': 'integer'})
        printer = self.client1.service_client("print_ints", {'type': 'array'}, {'type': 'string'})
        double  = self.client1.service_client("double_ints", {'type': 'array'}, {'type': 'array'})
        ret1 = yield task.deferLater(reactor, 0.5, adder, [4,5,6])
        ret2 = yield task.deferLater(reactor, 0.5, printer, ['a','b','c'])
        ret3 = yield task.deferLater(reactor, 0.5, double, [1, 2, 3])
        self.assertEqual(ret1, 15)
        self.assertEqual(ret2, "a b c")
        self.assertEqual(ret3, [2, 4, 6])

    @MiniBusTwistedClient.inlineServiceCallbacks
    def test_multiclients(self):
        adder = self.client1.service_client("add_ints", {'type': 'array'}, {'type': 'integer'})
        adder2 = self.client2.service_client("add_ints", {'type': 'array'}, {'type': 'integer'})
        ret1 = yield task.deferLater(reactor, 0.5, adder, [1,2,3])
        ret2 = yield task.deferLater(reactor, 0.5, adder2, [4,5,6])
        self.assertEqual(ret1, 6)
        self.assertEqual(ret2, 15)


# This is not working yet
# class TestChainedServices(unittest.TestCase):
#     @MiniBusTwistedClient.inlineServiceCallbacks
#     def service1(self, data):
#         data = data + " stuff"
#         call2val = yield self.call2(data)
#         defer.returnValue(call2val)
# 
#     def service2(self, data):
#         return data + " things"
# 
#     def setUp(self):
#         self.server1 = MiniBusTwistedClient()
#         self.server1.service("service1", {'type':'string'}, {}, self.service1)
#         self.client1 = MiniBusTwistedClient()
#         self.call1 = self.client1.service_client("service1",{'type':'string'}, {})
#         self.server2 = MiniBusTwistedClient()
#         self.server2.service("service2", {'type':'string'}, {'type':'string'}, self.service2)
#         self.client2 = MiniBusTwistedClient()
#         self.call2 = self.client2.service_client("service2",{'type':'string'}, {'type':'string'})
# 
# 
#     def tearDown(self):
#         a = self.server1._cleanup()
#         b = self.server2._cleanup()
#         c = self.client1._cleanup()
#         d = self.client2._cleanup()
# 
#     @MiniBusTwistedClient.inlineServiceCallbacks
#     def test_calls(self):
#         retval = yield task.deferLater(reactor, 0.5, self.call1, "mine")
#         self.assertEqual(retval, "mine stuff things")
# 
