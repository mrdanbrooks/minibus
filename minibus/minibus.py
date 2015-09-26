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

import logging
import logging.handlers
import re
import json
import jsonschema
import os
import random
import uuid
import netifaces as ni

FATAL = logging.FATAL
ERROR = logging.ERROR
WARNING = logging.WARNING
WARN = logging.WARN
INFO = logging.INFO
DEBUG = logging.DEBUG


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
    def __init__(self, name, cryptokey=None):
        """ Clients have a defined name """
        pass

    def publisher(self, topic_name, data_format):
        raise NotImplementedError()

    def subscribe(self, name_pattern, data_format, callback, headers=False):
        # Should return a reference to be used to remove the subscriber
        raise NotImplementedError()

    def unsubscribe(self, name_pattern, callback):
        raise NotImplementedError()

    def service_client(self, name, reqst_schema, reply_schema, reply_cb, err_cb):
        # This should set up resources for sending and receiving data with remote service
        # requester(params): Sends data to remote service. Returns srvid value
        # receiver(srvid, callback()
        raise NotImplementedError()

    def service_func_client(self, name, reqst_schema, reply_schema):
        """ Returns a function that behaves like a local function.
        retval = proxyfunc(params)
        """
        raise NotImplementedError()

    def service_server(self, name, reqst_schema, reply_schema, func):
        """ Provides a named network service. Service work is received by the
        func parameter, including an srvid value and received parameters.
        The srvid value is used to identify the client's "work order" information
        and must be passed to one of the two reply functions.
        Service returns value to client when a value is passed to either
        service_server_return() or service_server_error().
        """
        raise NotImplementedError()

    def service_func_server(self, name, reqst_schema, reply_schema, func):
        """ Provides a named network service linked to a local function.
        my_func(params...)
        Client receives the value returned by the function.
        This is a convenience function that wraps the functionality of service_server()
        around a single function which returns a value to be sent back to the client.
        """
        raise NotImplementedError()

    def service_server_return(self, srvid, value):
        """ Used by a service server to send a return value to a service client """
        raise NotImplementedError()

    def service_server_error(self, srvid, value):
        """ Used by a service server to send an error value to a service client """
        raise NotImplementedError()

data_header = {
    "title": "Data Header Object",
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "author": {"type": "string"},
        "gpg": {"type": "string"},
        "idstr": {"type": "string"},
        "version": {"enum": ["0.3.0"]}
    },
    "required": ["topic"]
}

busschema = {
    "title": "MiniBus Schema 0.3.0",
    "type": "object",
    "properties": {
        "header": data_header,
        "data": {"type": "string"},  # This is serialized json data
    },
    "required": ["header", "data"],
    "additionalProperties": False
}

class MiniBusClientCoreServices(object):
    """ Embedded Services """
    def __init__(self):
        self.service_func_server("/__minibus__/__listclients__",
                                 {"type": "null"},
                                 {"type": "string"},
                                 self.__get_name)
        self.service_func_server("/__minibus__/__publishers__",
                                 {"type": "null"},
                                 {"type": "array"},
                                 self.__get_publishers)
        self.service_func_server("/__minibus__/%s/__publishers__" % self._clientname,
                                 {"type": "null"},
                                 {"type": "array"},
                                 self.__get_publishers)
        self.service_func_server("/__minibus__/__subscribers__",
                                 {"type": "null"},
                                 {"type": "array"},
                                 self.__get_subscribers)
        self.service_func_server("/__minibus__/%s/__subscribers__" % self._clientname,
                                 {"type": "null"},
                                 {"type": "array"},
                                 self.__get_subscribers)
        self.service_func_server("/__minibus__/__service_servers__",
                                 {"type": "null"},
                                 {"type": "array"},
                                 self.__get_service_servers)
        self.service_func_server("/__minibus__/%s/__service_servers__" % self._clientname,
                                 {"type": "null"},
                                 {"type": "array"},
                                 self.__get_service_servers)
        self.service_func_server("/__minibus__/__service_clients__",
                                 {"type": "null"},
                                 {"type": "array"},
                                 self.__get_service_clients)
        self.service_func_server("/__minibus__/%s/__service_clients__" % self._clientname,
                                 {"type": "null"},
                                 {"type": "array"},
                                 self.__get_service_clients)
        self.service_func_server("/__minibus__/%s/__hostname__" % self._clientname,
                                 {"type": "null"},
                                 {"type": "string"},
                                 self.__get_hostname)
        self.service_func_server("/__minibus__/%s/__pid__" % self._clientname,
                                 {"type": "null"},
                                 {"type": "integer"},
                                 self.__get_pid)


    def __get_name(self, params):
        return self._clientname

    def __get_hostname(self, params):
        import socket
        return socket.gethostname()

    def __get_pid(self, params):
        return os.getpid()

    def __get_publishers(self, params):
        """ Service call function that returns a list of regular topic publishers by this client,
        not including topics related to services.
        """
        pubs = copy.deepcopy(self._publishers)
        # Remove publishers for services
        pubs = [p for p in pubs if p.split("/")[-1] not in ["__request__", "__reply__", "__error__"]]
        return pubs

    def __get_subscribers(self, params):
        # Subscription topics are stored in compiled regular expressions.
        # They are automatically bounded by the characters ^ and $ to delimit the string.
        # Turn keys into strings and remove the bounding characters so we can see the original string
        subs = [p.pattern[1:-1] for p in self._subscriptions.keys()]
        # Remove subscriptions for services
        subs = [s for s in subs if s.split("/")[-1] not in ["__request__", "__reply__", "__error__"]]
        return subs

    def __get_service_servers(self, params):
        subs = [p.pattern[1:-1] for p in self._subscriptions.keys()]
        subs = [s for s in subs if s.split("/")[-1] == "__request__"]
        # Just get the base name without the __request__, __reply__, __error__
        subs = [p[:p.rfind("/")] for p in subs]  
        # Filter out Built-in services
        subs = [s for s in subs if not re.match("^/__minibus__/", s)]
        return subs

    def __get_service_clients(self, params):
        pubs = copy.deepcopy(self._publishers)
        pubs = [p[:p.rfind("/")] for p in pubs if p.split("/")[-1] == "__request__"]
        # Filter out Built-in services
        pubs = [p for p in pubs if not re.match("^/__minibus__/", p)]
        return pubs



class MiniBusClientCore(MiniBusClientAPI, MiniBusClientCoreServices):
   #pylint: disable=no-self-use,no-member 
    def __init__(self, name=None, iface=None, cryptokey=None):
        # Set up Logging Mechanism
        self._logger = MBLagerLogger("MiniBus")
        self._logger.console(INFO)

        MiniBusClientAPI.__init__(self, name, iface)
        self._iface = iface
        self._clientname = name if name else str(uuid.uuid4())
        self._cryptokey = cryptokey
        if cryptokey:
            if not HAS_GNUPG:
                raise Exception("cryptokey was provided, but gnupg module not installed.")
            self._gpg = gnupg.GPG()

        self._subscriptions = dict()  # topicname(regex): callbacks(list(func))
        # topic patterns (subscriptions and publications) must have a single schema
        self._topic_schemas = dict()  # topicname(regex): jsonschema(dict)

        self._publishers = list()  # List of published topics: only for keeping track to be reported by __get_publishers
        # Services
        self._service_server_requests = dict()  # requestid(str): "servicetopicsharedname/"

        # Make sure our schema is good
        jsonschema.Draft4Validator.check_schema(busschema)

        # Start common services - this should only be done after everything else is loaded.
        MiniBusClientCoreServices.__init__(self)


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

    def _encrypt_data(self, plaintext):
        """ Encrypts data using gpg symmetric armored text. This is pretty bad and should be replaced """
        if not HAS_GNUPG:
            raise Exception("Attempting to encrypted packet, but I don't have gnupg")
        crypt = self._gpg.encrypt(plaintext, recipients=None, symmetric=True,
                            passphrase=self._cryptokey, armor=True)
        ciphertext = [x for x in crypt.data.split('\n') if len(x) > 0]
        # Remove the first and last lines
        # First line is -----BEGIN PGP MESSAGE-----
        # Last line is -----END PGP MESSAGE-----
        ciphertext = ciphertext[1:-1]
        # Second line is possibly Version: GnuPG vX.X.X - remove it
        if len(ciphertext) > 0 and len(ciphertext[0].strip()) > 0:
            if ciphertext[0].strip().lower()[:7] == "version":
                ciphertext = ciphertext[1:]
        # Combines all the lines into one long string of text
        return "".join(ciphertext)

    def _decrypt_data(self, ciphertext):
        """ Takes packet with armored symmetric gpg data and replaces it with plain text """
        # TODO: Instead of encrypting just the data in the message, we should probably be wrapping everything?
        if not HAS_GNUPG:
            raise Exception("Received encrypted packet that I can't decrypt")
        if not self._cryptokey:
            raise Exception("Received encrypted packet, but I don't have a key")
        # We are just sending the ciphertext and not the full message, so we need
        # to reconstructe it here before we can decrypt it
        ciphertext = "-----BEGIN PGP MESSAGE-----\n\n%s\n-----END PGP MESSAGE-----" % ciphertext
        plaintext = self._gpg.decrypt(ciphertext, passphrase=self._cryptokey)
        return plaintext

    
    def recv_packet(self, datagram):
        self._logger.debug("Received datagram=%s" % datagram)
        # Check for empty data packets
        if len(datagram.strip()) == 0:
            self._logger.debug("Datagram was empty")
            return
        # Deserialize packet
        packet = json.loads(datagram)
        # Check packet schema
        jsonschema.validate(packet, busschema)
        topic = packet["header"]["topic"]
        header = packet["header"]
        data = packet["data"]
        for pattern, callbacks in self._subscriptions.items():
            if pattern.match(topic):
                # Make sure encapsulated data matches user specified schema
                user_schema = self._topic_schemas[pattern]
                self._logger.debug("Found matching pattern %s that will use schema %s "
                             % (pattern.pattern, user_schema))
                # Decrypt data
                if "gpg" in packet["header"]:
                    data = self._decrypt_data(data)
                    data = data.data
                # Deserialize data
                data = json.loads(data)
                # Validate data
                jsonschema.validate(data, user_schema)
                # push data to all the callbacks for this pattern (in a random order)
                index_order = range(len(callbacks))
                random.shuffle(index_order)
                for i in index_order:
#                     callbacks[i](header, data)
                    #NOTE: This was changed out for the above because socket
                    # implementation of service_func_client would hang waiting
                    # for a response in mbtt. This fixes it, although I have not
                    # traced the exact reason why the above was not working
                    self._run_callback(callbacks[i], header, data)

    def send_packet(self, datagram):
        raise NotImplementedError()

    def _publish(self, name, idstr, data):
        """ Serialize data and publish on topic of given name.
        This function is wrapped in a lambda expression and returned by publisher()
        """
        # Make sure this data conforms to user schema
        self._logger.debug("Attempting to publish %s" % data)
        for pattern, schema in self._topic_schemas.items():
            if pattern.match(name):
                self._logger.debug("found matching pattern %s" % pattern.pattern)
                jsonschema.validate(data, schema)
        # Serialize
        data = json.dumps(data)
        # Encrypt
        if self._cryptokey:
            data = self._encrypt_data(data)
        # Packetize
        packet = {"header": {"topic": name, "author": self._clientname, "idstr": idstr}, "data": data}
        if self._cryptokey:
            packet["header"]["gpg"] = 'yes'
        jsonschema.validate(packet, busschema)
        # Serialize
        packet = json.dumps(packet)
        # NOTE: This assumes all data is being sent locally over the control bus.
        #       it needs updated to transmit over specific tcp ports eventually
        self.send_packet(packet)
        self._logger.debug("Packet sent!")

    def subscribe(self, name_pattern, data_format, callback, headers=False):
        """ Instructs client to listen to topic matching 'topic_name'.
            name_pattern (str): regex to match topic name against
            data_format (dict): jsonschema to validate incomming data types
            callback (func): function that will be called to receive the data
            headers: When True, callback function should have signature func(headers, data),
                     otherwise func(data)
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

        # If we don't want to deal with header data, wrap the callback function
        # before adding it to the subscriptions list
        if headers:
            self._subscriptions[pattern].append(callback)
        else:
            simple = lambda header, data, func=callback: callback(data) 
            self._subscriptions[pattern].append(simple)


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
        # Keep track of publishers in a list so we can tell people what we publish
        # to at a later time
        self._publishers.append(topic_name)
        return lambda data: self._publish(topic_name, str(uuid.uuid4()), data)

    ########################
    ## Services Functions ##
    ########################

    def _srv_namespacing(self, name):
        """ Returns tuple of service topic names (request, reply, error)
        Services share a common namespace <name> with three well known topic
        names inside it. 
        """
        if not (isinstance(name, str) or isinstance(name, unicode)):
            raise Exception("Service name must be a string, not '%s'" % str(type(name)))
        # Add a / to the end if it doesn't already exist
        name += "/" if not name[-1] == "/" else ""
        return (name + "__request__", name + "__reply__", name + "__error__")

    def service_func_server(self, name, reqst_schema, reply_schema, func):
        def _srv_fun(reqstid, params, func):
            retval = func(params)
            self.service_server_return(reqstid, retval)

        srv_fun = lambda reqstid, params, f=func: _srv_fun(reqstid, params, f)
        self.service_server(name, reqst_schema, reply_schema, srv_fun)

    def service_server(self, name, reqst_schema, reply_schema, func):
        # TODO: add information to a list of services this node provides?
        def _srv_cb(headers, reqst_data, func):
            try:
                # Save the work request with the topic you received it on by
                # striping the "__request__" part off the topic string, saving the /
                self._service_server_requests[headers["idstr"]] = headers["topic"][:-11]
                func(headers["idstr"], reqst_data)
            except Exception as e:
                self.service_server_error(headers["idstr"], str(e))
                raise e
            else:
                # TODO: test if work id still exists. If it does, set a timer
                # to check on it again. If it still exists after the timer expires,
                # do the service_server_error() at that point in time and remove it.
                pass
        # Get topic names
        request_topic, reply_topic, error_topic = self._srv_namespacing(name)

        # Create publishers for sending reply to service clients
        # NOTE: Even if we don't ever use these again, it checks the schemas to
        # make sure they are well formed and registers the schema to the topic
        self.publisher(reply_topic, reply_schema)
        self.publisher(error_topic, { })  # TODO: Create a service error schema

        # Wrap the initial service function in a try/except, and subscribe it to
        # the request topic to listen for incoming queries
        srv_cb = lambda headers, reqst_data, f=func: _srv_cb(headers, reqst_data, f)
        self.subscribe(request_topic, reqst_schema, srv_cb, headers=True)

    def service_server_return(self, reqstid, value):
        # Normally we should not directly use the _publish command because it makes
        # assumptions that the topic being published on has been initialized by
        # a call to self.publisher() first. But we do that and this feels cleaner
        # then keeping track of extra publisher objects

        # Remove the service request from the list and use it to generate the topic
        # name we will reply on
        reply_topic = self._srv_namespacing(self._service_server_requests.pop(reqstid))[1]
        self._publish(reply_topic, reqstid, value)


    def service_server_error(self, reqstid, value):
        # Normally we should not directly use the _publish command because it makes
        # assumptions that the topic being published on has been initialized by
        # a call to self.publisher() first. But we do that and this feels cleaner
        # then keeping track of extra publisher objects

        # Remove the service request from the list and use it to generate the topic
        # name we will reply on
        error_topic = self._srv_namespacing(self._service_server_requests.pop(reqstid))[2]
        self._publish(error_topic, reqstid, value)

    def service_client(self, name, reqst_schema, reply_schema, reply_cb, err_cb):
        def _srv_request(data, topic_name):
            """ This is similar to what a publisher returns, except this gives you the uuid back """
            #TODO: publishers don't return anything normally, should we just do this all the time
            # instead of making it a special case here?
            reqstid = str(uuid.uuid4())
            request_topic = self._srv_namespacing(name)[0]
            self._publish(request_topic, reqstid, data)
            return reqstid

        # Get topic names
        request_topic, reply_topic, error_topic = self._srv_namespacing(name)

        # Create publishers and subscribers. We don't keep the publishers but
        # this initializes them and registers their schemas
        self.publisher(request_topic, reqst_schema)

        reply_cb_wrapper = lambda headers, data, cb_func=reply_cb: cb_func(headers["idstr"], data)
        err_cb_wrapper = lambda headers, data, cb_func=err_cb: cb_func(headers["idstr"], data)
        self.subscribe(reply_topic, reply_schema, reply_cb_wrapper, headers=True)
        self.subscribe(error_topic, { }, err_cb_wrapper, headers=True)

        # Return a function to "call" the service with
        return lambda data, name=name: _srv_request(data, name) 




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
            MiniBusClientCore.__init__(self, name=name, cryptokey=cryptokey)
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

        def service_func_client(self, name, reqst_schema, reply_schema):
            """ This implementation is somewhat specific to twisted """
            class ServiceFuncClient(object):
                def __init__(self, mbclient, name, reqst_schema, reply_schema):
                    self.mbclient = mbclient
                    self.name = name
                    self.callpub = self.mbclient.service_client(name, reqst_schema, reply_schema, self.reply_cb, self.err_cb)
                    self._service_callbacks = dict()

                def reply_cb(self, idstr, data):
                    if idstr in self._service_callbacks.keys():
                        self._service_callbacks[idstr].callback(data)
                    #TODO: If thing not listed, set timer and try again

                def err_cb(self, idstr, data):
                    #TODO: Implement this
                    self.reply_cb(idstr, data)  # Punt by sending error data to reply callback
                    raise Exception("Implement Twisted Service Client Errors")


                @defer.inlineCallbacks
                def __call__(self, data):
                    idstr = self.callpub(data)
                    d = defer.Deferred()
                    self._service_callbacks[idstr] = d
                    # Wait for reply
                    ret = yield d
                    self._service_callbacks.pop(idstr)
                    defer.returnValue(ret)

            return ServiceFuncClient(self, name, reqst_schema, reply_schema)

        def send_packet(self, data):
            self._logger.debug("Asserting that we are running")
            self._assert_running()
            self._logger.debug("Writing to transport")
            self.datagram_protocol.transport.write(data, ("228.0.0.5", 8005))
            self._logger.debug("Finished")

        def _assert_running(self):
            """ Check to make sure the reactor is running before continuing """
            if not reactor.running:
                raise Exception("This API call must only be called after start()")

        def _run_callback(self, cb, header, data):
            reactor.callLater(0, cb, header, data)

        def exec_(self):
            reactor.run()

        def _cleanup(self):
            # This was found via trail and error using suggestions from
            # http://blackjml.livejournal.com/23029.html
            listenerDeferred = self._multicastListener.stopListening()
            return listenerDeferred

        def exit_(self):
            self._cleanup()
            self._logger.debug("Disconnecting MiniBus Client")
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
        MiniBusClientCore.__init__(self, name=name, cryptokey=cryptokey)
        self.addrinfo = socket.getaddrinfo("228.0.0.5", None)[0]
        self.s = socket.socket(self.addrinfo[0], socket.SOCK_DGRAM)

        # Allow multiple copies of this program on one machine
        # (not strictly needed)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # This is used in the twisted framework and fixes the single connection problem in osx
        # twisted/internet/udp.py MulticastPort().createInternetSocket()
        # http://twistedmatrix.com/trac/browser/tags/releases/twisted-14.0.1/twisted/internet/udp.py
        if hasattr(socket, "SO_REUSEPORT"):
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

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
        self._lock = threading.Lock()
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

    def service_func_client(self, name, reqst_schema, reply_schema):
        """ This implementation is somewhat specific to the threaded sockets """
        class ServiceFuncClient(object):
            def __init__(self, mbclient, name, reqst_schema, reply_schema):
                self.mbclient = mbclient
                self._service_replies = dict()
                self.callpub = self.mbclient.service_client(name, reqst_schema, reply_schema, self.reply_cb, self.err_cb)
                self._lock = threading.Lock()
                self._error = False

            def reply_cb(self, idstr, data):
#                 with self._lock:
#                     print "submitted", data
                self._service_replies[idstr] = data
                # TODO IF thing not listed, set timer and try again?

            def err_cb(self, idstr, data):
                # TODO: This is a real dirty way of doing this
                self._error = True

            def __call__(self, data):
                idstr = self.callpub(data)
                self._error = False
                while self.mbclient._running and not self._error:
                    if idstr in self._service_replies.keys():
                        break
                    time.sleep(0.001)
                if not self.mbclient._running:
                    raise Exception("Shutting down") 

                if self._error:
                    raise NotImplementedException("Implemented this error")

                with self._lock:
                    return self._service_replies.pop(idstr)
        return ServiceFuncClient(self, name, reqst_schema, reply_schema)


    def send_packet(self, data):
        self._logger.debug("Writing to transport")
        self.s.sendto(data + '\n', (self.addrinfo[4][0], 8005))
        self._logger.debug("Finished")

    def _run_callback(self, cb, header, data):
        thread = threading.Thread(target=cb, args=(header, data))
        thread.start()

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
        with self._lock:
            if self.s:
                try:
                    self.s.shutdown(socket.SHUT_RD)
                except socket.error:
                    # If the above fails, we hang at recv. Send an empty packet to release it.
                    self.s.sendto('\n', (self.addrinfo[4][0], 8005))
                self.s.close()
                self.s = None  # Prevent socket from trying to be closed a second time
        # If called from the main thread, join with receiver before exiting
        if not threading.current_thread() == self._recv_thread:
            self._recv_thread.join()


class MBLagerLogger(logging.Logger):
    """ King of Loggers - Embedded in Minibus to reduce dependencies """
    def __init__(self, name, level=None):
        logging.Logger.__init__(self, name, self.__level(level))
        self.formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S")

    def __level(self, lvl):
        return lvl if lvl is not None else logging.DEBUG

    def console(self, level):
        """ adds a console handler """
        ch = logging.StreamHandler()
        ch.setLevel(self.__level(level))
        ch.setFormatter(self.formatter)
        self.addHandler(ch)

    def logfile(self, level, path=None):
        if path is None:
            path = "log.log"
        path = os.path.normpath(os.path.expanduser(path))
        try:
            # Attempt to set up the logger with specified log target
            open(path, "a").close()
            hdlr = logging.handlers.RotatingFileHandler(path, maxBytes=500000, backupCount=5)
            hdlr.setLevel(self.__level(level))
            hdlr.setFormatter(self.formatter)
        except IOError:
            logging.error('Failed to open file %s for logging' % logpath, exc_info=True)
            sys.exit(1)
        self.addHandler(hdlr)

