#   Copyright 2015 Dan Brooks
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

""" minibus """
# This is a port of the minibus2.py file from homesec, with some additional comments
# for adding service functionality

import re
import json
import jsonschema
import os
import random
import uuid
import netifaces as ni

import lagerlogger
logger = lagerlogger.LagerLogger("MiniBusClient")
logger.console(lagerlogger.INFO)

try:
    import gnupg  # Install with python-gnupg or py27-gnupg
    HAS_GNUPG = True
except ImportError:
    HAS_GNUPG = False

try:
    from twisted.internet.protocol import DatagramProtocol
    from twisted.internet import reactor, defer
    HAS_TWISTED = True
except ImportError:
    HAS_TWISTED = False


class MiniBusClientAPI(object):
    """ Defines the public API for interacting with the minibus """
    def __init__(self, name, iface=None):
        """ Clients have a defined name """
        pass

    def publisher(self, topic_name, data_format):
        raise NotImplementedError()

    def subscribe(self, name_pattern, data_format, callback, headers=False):
        # Should return a reference to be used to remove the subscriber
        raise NotImplementedError()

    def unsubscribe(self, name_pattern, callback):
        raise NotImplementedError()

    def service_client_func(self, name, reqst_schema, reply_schema):
        """ Returns a function for calling a remote service """
        # request(srv_reqst_pub, reqst_schema, data):
        #    srvid = uuid.uuid4()
        #    # Create publisher
        #    srv_reqst_pub = self.publisher(name+"__request__", reqst_schema)
        #
        #    # Create subscriber
        #    def reply_receiver(srvid, data):
        #        # TODO: Somehow make sure we are waiting on this srvid
        #        self.srv_replies[srvid] = data
        #        self.unsubscribe(selfptr)
        #    srv_reply_recver = lambda reply_receiver(srvid, data)
        #    self.subscribe(name+"__reply__", reply_schema, reply_receiver)
        #
        #    reqst_packet = reqstwrapp(name, srvid, data)
        #    srv_reqst_pub(reqst_packet)
        #    while(wait and srvid not in self.srv_replies.keys() and srvid not in self.srv_errors.keys()):
        #        sleep
        #    if srvid not in self.srv_replies.keys()
        #         raise Exception
        #    if srvid not in self.srv_errors.keys()
        #         raise Exception
        #    retval = self.srv_replies[srvid]
        #    pop(self.srv_replies[srvid])
        #    return retval
        raise NotImplementedError()

    def service_client(self, name, reqst_schema, reply_schema):
        # This should set up resources for sending and receiving data with remote service
        # requester(params): Sends data to remote service. Returns srvid value
        # receiver(srvid, callback()
        raise NotImplementedError()

    def service_func_client(self, name, reqst_schema, reply_schema):
        """ Returns a function that behaves like a local function.
        retval = proxyfunc(params)
        """
        raise NotImplementedError()

    def service_cb_client(self, name, reqst_schema, reply_schema, callback, errback):
        """ Returns a function to call the service with. Replies are received in callbacks.
            proxyfunc(param): returns srvid that will be received by callbacks along with reply
        """
        # the proxy func and callbacks all need to be wrapped in something for
        # encoding and decoding the service packet
        raise NotImplementedError()

    def service_func_server(self, name, reqst_schema, reply_schema, func):
        """ Provides a named network service linked to a local function.
        my_func(params...)
        Client receives the value returned by the function.
        This is a convenience function that wraps the functionality of service_server()
        around a single function which returns a value to be sent back to the client.
        """
        # CODE TO BE PUT IN CLIENT CORE
        # def _srv_fun(func, headers, reqst):
        #    retval = func(reqst.params)
        #    service_server_return(reqst.id, retval)
        #
        # srvfun = lambda headers,params,f=func: _srv_fun(f, headers, params) 
        # self.service_server(name, reqst_schema, reply_schema, srvfun)
        raise NotImplementedError()

    def service_server(self, name, reqst_schema, reply_schema, func):
        """ Provides a named network service. Service work is received by the
        func parameter, including an srvid value and received parameters.
        The srvid value is used to identify the client's "work order" information
        and must be passed to one of the two reply functions.
        Service returns value to client when a value is passed to either
        service_server_return() or service_server_error().
        """
        # CODE TO BE PUT IN CLIENT CORE
        # def _srv_cb(headers, reqst, func):
        #    self.srv_workers[reqst.id] = headers.topic - "__request__"   (unset in server_server_return/error)
        #    try:
        #        func(reqst.params)
        #    except Exception as e:
        #        service_server_error(reqst.id, str(e)) 
        #    else:
        #        TODO: test if work id still exists. If it does, set a timer
        #        to check on it again. If it still exists after the timer expires,
        #        do the service_server_error() at that point in time and remove it.
        #
        # # Create Publishers for sending replys
        # srv_reply_pub = self.publisher(name+"__reply__", reply_schema)
        # srv_error_pub = self.publisher(name+"__error__", { })
        # self.srv_pubs[name] = (srv_reply_pub, srv_error_pub)
        #
        # srvfun = lambda headers, reqst, f=func: _srv_cb(headers, reqst, f)
        # self.subscribe(name+"__request__", reqst_schema, srvfun, headers = True)
        # TODO: add information to a list of services this node provides
        raise NotImplementedError()

    def service_server_return(self, srvid, value):
        """ Used by a service server to send a return value to a service client """
        raise NotImplementedError()

    def service_server_error(self, srvid, value):
        """ Used by a service server to send an error value to a service client """
        raise NotImplementedError()

    def client_info(self, name):
        raise NotImplementedError()

data_header = {
    "title": "Data Header Object",
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "author": {"type": "string"},
        "gpg": {"type": "string"},
        "idstr": {"type": "string"}
    },
    "required": ["topic"]
}

busschema = {
    "title": "MiniBus Schema",
    "type": "object",
    "properties": {
        "version": "3.0.0",
        "header": data_header,
        "data": {},
    },
    "required": ["header", "data"],
    "additionalProperties": False
}


class MiniBusClientCore(MiniBusClientAPI):
   #pylint: disable=no-self-use,no-member 

    def __init__(self, name, iface=None, cryptokey=None):
        MiniBusClientAPI.__init__(self, name, iface)
        self._iface = iface
        self._clientname = name
        self._cryptokey = cryptokey
        if cryptokey:
            if not HAS_GNUPG:
                raise Exception("cryptokey was provided, but gnupg module not installed.")
            self._gpg = gnupg.GPG()

        self._subscriptions = dict()  # topicname(regex): callbacks(list(func))
        # topic patterns (subscriptions and publications) must have a single schema
        self._topic_schemas = dict()  # topicname(regex): jsonschema(dict)

        # Services
        self._local_services = dict()  # servicename(str): func
        self._service_schemas = dict()  # servicename(str): (req_schema, reply_schema)
        self._service_callbacks = dict()

        # Make sure our schema is good
        jsonschema.Draft4Validator.check_schema(busschema)

    def _get_iface_ip(self):
        """ Returns the ip address for a named interface """
        if self._iface not in ni.interfaces():
            raise Exception("Interface %s not found" % self._iface)
        return ni.ifaddresses(self._iface)[ni.AF_INET][0]['addr']

    def _get_name_pattern(self, name_pattern):
        """ automatically adds a ^ to begining and $ to end of name_patterns if needed """
        if not name_pattern[0] == '^':
            name_pattern = '^' + name_pattern
        if not name_pattern[-1] == '$':
            name_pattern = name_pattern + '$'
        # Make sure topic_name is a valid regex
        pattern = re.compile(name_pattern)
        return pattern

    def _decrypt_packet(self, packet):
        """ Takes packet with armored symmetric gpg data and replaces it with plain text """
        # TODO: Instead of encrypting just the data in the message, we should probably be wrapping everything?
        if not HAS_GNUPG:
            raise Exception("Received encrypted packet that I can't decrypt")
        if not self._cryptokey:
            raise Exception("Received encrypted packet, but I don't have a key")
        gpgversion = packet["header"]["gpg"]
        gpgtext = packet["data"]
        ciphertext = gpg.decrypt(packet["data"], self._cryptokey)
        # We are just sending the ciphertext and not the full message, so we need
        # to reconstructe it here before we can decrypt it
        ciphertext = "-----BEGIN PGP MESSAGE-----\nVersion: %s\n\n%s\n-----END PGP MESSAGE-----" % (gpgversion, gpgtext)
        plaintext = gpg.decrypt(ciphertext, passphrase=self._cryptokey)
        packet["data"] = plaintext
        return packet

    def _encrypt_packet(self, packet):
        """ Takes packet with plain text data and replaces it with encrypted symmetric armored text """
        if not HAS_GNUPG:
            raise Exception("Attempting to encrypted packet, but I don't have gnupg")
        plaintext = packet["data"]
        crypt = gpg.encrypt(plaintext, recipients=None, symmetric=True,
                            passphrase=self._cryptokey, armor=True)
        ciphertext = [x for x in crypt.data.split('\n') if len(x) > 0]
        # First line is -----BEGIN PGP MESSAGE-----
        # Second line is Version: GnuPG vX.X.X
        # Last line is -----END PGP MESSAGE-----
        packet["header"]["gpg"] = ciphertext[1][9:].strip()  # Populate with version
        ciphertext = "".join(crypt[2:-1])  # Combines all the lines into one long string of text
        packet["data"] = ciphertext
        return packet

    def recv_packet(self, datagram):
        logger.debug("Received datagram=%s" % datagram)
        packet = json.loads(datagram)
        jsonschema.validate(packet, busschema)
        if "gpg" in packet["header"]:
            packet = self._decrypt_packet(packet)

        topic = packet["header"]["topic"]
        data = packet["data"]
        for pattern, callbacks in self._subscriptions.items():
            if pattern.match(topic):
                # Make sure encapsulated data matches user specified schema
                user_schema = self._topic_schemas[pattern]
                logger.debug("Found matching pattern %s that will use schema %s "
                             % (pattern.pattern, user_schema))
                jsonschema.validate(data, user_schema)
                # push data to all the callbacks for this pattern (in a random order)
                index_order = range(len(callbacks))
                random.shuffle(index_order)
                for i in index_order:
                    #TODO: Spawn in new thread, then wait for all to join before exiting
                    callbacks[i](header, data)

    def send_packet(self, datagram):
        raise NotImplementedError()

    def _publish(self, name, data):
        """ Serialize data and publish on topic of given name.
        This function is wrapped in a lambda expression and returned by publisher()
        """
        # Make sure this data conforms to user schema
        logger.debug("Attempting to publish %s" % data)
        for pattern, schema in self._topic_schemas.items():
            if pattern.match(name):
                logger.debug("found matching pattern %s" % pattern.pattern)
                jsonschema.validate(data, schema)

#         packet = {"type": "data", "topic": name, "data": data}
        packet = {"header": {"topic": name, "author": self._clientname}, "data": data}
        jsonschema.validate(packet, busschema)
        # Encrypt if key specified
        if self._cryptokey:
            packet = self._encrypt_packet(packet)

        # Serialize
        packet = json.dumps(packet)
        # TODO: This assumes all data is being sent locally over the control bus.
        #       it needs updated to transmit over specific tcp ports eventually
        # TODO: Check to see if we have a matching data type?
        self.send_packet(packet)
        logger.debug("Packet sent!")

    def subscribe(self, name_pattern, data_format, callback):
        """ Instructs client to listen to topic matching 'topic_name'.
            name_pattern (str): regex to match topic name against
            data_format (dict): jsonschema to validate incomming data types
            callback (func): function that will be called to receive the data
        """
        pattern = self._get_name_pattern(name_pattern)

        # Make sure topic_type is a valid schema and matches existing pattern definitions
        # Within a client these must be consistant, however different clients can define
        # less strict schema to match against
        jsonschema.Draft4Validator.check_schema(data_format)
        if pattern not in self._topic_schemas:
            self._topic_schemas[pattern] = data_format
        elif not data_format == self._topic_schemas[pattern]:
            raise Exception("Conflicting schema already exists for %s" % name_pattern)

        # If are not already listening to this pattern, create a callback list
        if pattern not in self._subscriptions:
            self._subscriptions[pattern] = list()
        # Make sure we don't have multiple of the same callback
        if callback in self._subscriptions[pattern]:
            raise Exception("Callback %s already registered for subscription  %s"
                            % (str(callback), name_pattern))
        self._subscriptions[pattern].append(callback)

    def unsubscribe(self, name_pattern, callback):
        pattern = self._get_name_pattern(name_pattern)
        try:
            self._subscriptions[pattern].remove(callback)
        except ValueError:
            print "callback not found for this topic"

    def publisher(self, topic_name, data_format):
        """
        Returns a function to publish data on this topic.
        NOTE: This does not check types over the network
        """
        pattern = self._get_name_pattern(topic_name)
        jsonschema.Draft4Validator.check_schema(data_format)
        if pattern in self._topic_schemas:
            if not data_format == self._topic_schemas[pattern]:
                raise Exception("Conflicting schema already exists for %s" % topic_name)
        else:
            self._topic_schemas[pattern] = data_format
        return lambda data: self._publish(topic_name, data)


# Service calls are hard to make generic between the two models because there is inheriently
# the problem that the service call could call yet another service (chaining) and hang because
# it does not return right away.

class TopicServiceHost(object):
    def __init__(self, service):
        self._reqst_topic = None
        self._reply_topic = None
        self._error_topic = None
        self.reply_pub = self.publisher("/test/reply", {})
        self.error_pub = self.publisher("/test/error", {})
        self.subscribe("/test/reqst", {}, self.service_call)
        self.service = service
        self.service_host("/test", {}, {}, self.service)

    def service(self, indata):
        return sum(indata)

    def service_call(self, header, data):
        try:
            # This call should really be threaded, but the symantics of that are complicated unless
            # this callback is already happening in a thread
            result = self.service(data)
            self.reply_pub(result)
        except Exception as e:
            self.error_pub(e)
        

class TopicServiceClient(object):
    def __init__(self):
        self._reqst_topic = None
        self._reply_topic = None
        self._error_topic = None
        self.pub = self.publisher("/test/reqst", { })
        self.subscribe("/test/reply", { }, self.callback)
        self.subscribe("/test/error", { }, self.callback)

    def callback(self, header, data):
        if header["topic"] == "/test/reply"

    def call(self, data=None):
        self.pub(data) # Does not have mechanism for setting transid like this
                        # unelss that was moved to inside a service specific wrapper

if HAS_TWISTED:
    class MiniBusTwistedClient(MiniBusClientCore):
        """ Twisted client for MiniBus.
        This class tries to hide most if not all of the twisted api specific things. """
        class MBDatagramProtocol(DatagramProtocol):
            """ This is the twisted DatagramProtocol for connecting """
            def __init__(self, client):
                self.mbclient = client

            def startProtocol(self):
                # Listen Locally
                self.transport.joinGroup("228.0.0.5")
                # If other interfaces are specified, listen to those as well
                # NOTE: This seems to work in linux, but maybe not in OSX? Unclear
                listening_addresses = list()
                if isinstance(self.mbclient._iface, str):
                    listening_addresses.append(self.mbclient._get_iface_ip())
                elif isinstance(self.mbclient._iface, list):
                    for iface in self.mbclinet._iface:
                        listening_addresses.append(self._get_iface_ip(iface))
                for ipaddr in listening_addresses:
                    self.transport.joinGroup("228.0.0.5", ipaddr)

            def datagramReceived(self, datagram, address):
                self.mbclient.recv_packet(datagram)

        def __init__(self, name=None, cryptokey=None):
            MiniBusClientCore.__init__(self, name, cryptokey)
            self.datagram_protocol = MiniBusTwistedClient.MBDatagramProtocol(self)

            # If there is a fini() defined, run it at shutdown
            if hasattr(self, "fini"):
                reactor.addSystemEventTrigger('during', 'shutdown', self.fini)

            # Start multicast datagram receiver
            self._multicastListener = reactor.listenMulticast(8005,
                                                              self.datagram_protocol,
                                                              listenMultiple=True)

            # If there is an init() defined, call it as soon as the reactor starts up.
            # If there is a run() defined, call it when the reactor starts up
            if hasattr(self, "run") and callable(getattr(self, "run")):
                reactor.callInThread(self.run)

        def send_packet(self, data):
            logger.debug("Asserting that we are running")
            self._assert_running()
            logger.debug("Writing to transport")
            self.datagram_protocol.transport.write(data, ("228.0.0.5", 8005))
            logger.debug("Finished")

        def _assert_running(self):
            """ Check to make sure the reactor is running before continuing """
            if not reactor.running:
                raise Exception("This API call must only be called after start()")

        def exec_(self):
            reactor.run()

        def _cleanup(self):
            # This was found via trail and error using suggestions from
            # http://blackjml.livejournal.com/23029.html
            listenerDeferred = self._multicastListener.stopListening()
            return listenerDeferred

        def exit_(self):
            self._cleanup()
            logger.debug("Disconnecting MiniBus Client")
            reactor.stop()

        @staticmethod
        def inlineServiceCallbacks(fun):
            """ Used to decorate functions that use service callbacks """
            return defer.inlineCallbacks(fun)


import time
import struct
import socket
import sys
import threading
import select
import copy


class MiniBusSocketClient(MiniBusClientCore):
    """
    Threaded socket version of the MiniBusClient.
    Based on code from:
    http://svn.python.org/projects/python/trunk/Demo/sockets/mcast.py
    https://ep2013.europython.eu/media/conference/slides/using-sockets-in-python.html
    """
    def __init__(self, name=None, cryptokey=None):
        MiniBusClientCore.__init__(self, name, cryptokey)
        self.addrinfo = socket.getaddrinfo("228.0.0.5", None)[0]
        self.s = socket.socket(self.addrinfo[0], socket.SOCK_DGRAM)

        # Allow multiple copies of this program on one machine
        # (not strictly needed)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Set Time-to-live (optional)
        self.ttl_bin = struct.pack('@i', 1)
        if self.addrinfo[0] == socket.AF_INET:  # IPv4
            self.s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.ttl_bin)
        else:
            self.s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, self.ttl_bin)

        # Bind it to the port for receiving
        self.s.bind(('', 8005))
        group_bin = socket.inet_pton(self.addrinfo[0], self.addrinfo[4][0])
        # Join group
        if self.addrinfo[0] == socket.AF_INET: # IPv4
            mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
            self.s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        else:
            mreq = group_bin + struct.pack('@I', 0)
            self.s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

        # Start receiving thread
        self._running = False
        self._recv_thread = threading.Thread(target=self.recv_thread)
        self._recv_thread.start()

#     def conn_thread(self):
#         self._running = True
#         rpipe, wpipe = os.pipe()
#         while self._running:
#             readable, writable, _ = select.select([rpipe, self.s], [wpipe], [], 60)
#             if self.s in readable:
#                 data, sender = self.s.recvfrom(1500)
#                 while data[-1:] == '\n': 
#                     data = data[:-1] 
#                 data = copy.deepcopy(data)
#                 self.recv_packet(data)
#             time.sleep(.00001)

    def recv_thread(self):
        """ receive incomming data """
        self._running = True
        self.s.setblocking(1)
        while self._running:
            data = self.s.recv(1500)
            while data[-1:] == '\n':
                data = data[:-1]
            data = copy.deepcopy(data)
            if data:
                self.recv_packet(data)

    def send_packet(self, data):
        logger.debug("Writing to transport")
        self.s.sendto(data + '\n', (self.addrinfo[4][0], 8005))
        logger.debug("Finished")

    def spin(self):
        """ A function to keep the main thread alive until keyboard interrput """
        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            return

    def close(self):
        """ Properly shutdown all the connections """
        self._running = False
        try:
            self.s.shutdown(socket.SHUT_RD)
        except socket.error:
            pass
        self.s.close()
        self._recv_thread.join()


