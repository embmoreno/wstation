import time
import zmq
from zmq.devices.basedevice import ProcessDevice
from zmq.devices.monitoredqueuedevice import MonitoredQueue
from zmq.utils.strtypes import asbytes
import random
import numpy as np
import json

class ZMQ_for_WeatherStation:
    
    # we will have 2 clients:
    # client 1: actual client pushing data to the server
    # client 2: an example client that will be replaced by ATHENA counterpart. This is only for testing.

    def __init__(self):
        self.frontend_port = 7559
        self.backend_port  = 7560
        self.monitor_port  = 7562
        self.number_of_clients = 2
        self.recorded_data     = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

    def monitordevice(self):
        in_prefix=asbytes('in')
        out_prefix=asbytes('out')
        monitoringdevice = MonitoredQueue(zmq.XREP, zmq.XREQ, zmq.PUB, in_prefix, out_prefix)
        
        monitoringdevice.bind_in("tcp://127.0.0.1:%d" % self.frontend_port)
        monitoringdevice.bind_out("tcp://127.0.0.1:%d" % self.backend_port)
        monitoringdevice.bind_mon("tcp://127.0.0.1:%d" % self.monitor_port)
        
        monitoringdevice.setsockopt_in(zmq.SNDHWM, 1)
        monitoringdevice.setsockopt_out(zmq.SNDHWM, 1)
        monitoringdevice.start()  
        print("Program: Monitoring device has started")

    def message_type(self, msg):
        # the message content expects the first part to be an identifier
        # [data-push] for data pushed from the datalogger
        # [data-rep]  for acknowledging datalogger for receive
        # [data-req]  for pulling data from the message queue
        # more message types may be needed in the future
        #
        # the content of the messages is as follows:
        # for [data-push]: [UNIX_TIMESTAMP, Measurement1, Measurement2, ...]
        # for [data-rep]:  list of last 3 measurements in the same format as [data-push]
        # for [data-req]:  no format, it is a simple request for data
        # depending on new message types, these formats may change
        #
        parse_msg = msg.split()
        return parse_msg[0], parse_msg[1]
    
    def server(self, backend_port):
        print("Program: Server connecting to device")
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.connect("tcp://127.0.0.1:%s" % self.backend_port)
        server_name = "gateway"
        while True:
            message = socket.recv()
            msg_type, msg_content = self.message_type(message)
            if msg_type == "[data-push]":
                socket.send("[response] new data received and put in queue")
                # get the new data as a list
                # remove the first entry to open space for the next one
                # append the new measurement to the end of the list
                # this will keep the last 3 measurements in a buffer
                # at this point, there is no need to increase this
                # may need to reconsider when it is needed
                new_data = np.fromstring(msg_content, dtype=float, sep=",")
                del self.recorded_data[0]
                self.recorded_data.append(new_data.tolist())
            if msg_type == "[data-req]":
                # send the recorded data to the ATHENA client
                # it is a list with last three measurements
                # for making it easier we can drop this to one entry
                # however, it might be good to have more to catch missing data
                socket.send("[data-rep] {}".format(self.recorded_data))

    # this function is for debigging purposes. In near real-time operation,
    # datalogger will have this code embedded in it.
    def client_datalogger(self, frontend_port):
        print("Program: datalogger")
        # for testing purposes, we will push data 3 times
        # wait 5 sec between each push
        for i in range(3):
            # this client is an emulator that dumps random measurements for now
            # this will be disabled in the script once the datalogger code can do this job
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect("tcp://127.0.0.1:%s" % frontend_port)
            socket.send ("[data-push] 1516727520.778591,2.0,3.0,4.0")
            #  Get the reply.
            message = socket.recv_multipart()
            time.sleep(5)

    # this function is for debugging purposes. In near real-time operation,
    # ATHENA script will be requesting and handling data
    def client_athena(self, frontend_port):
        # this client is for retrieving data from the queue
        print("Program: athena reader")
        # purposefully wait for 10 sec
        time.sleep(10)
        try:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect("tcp://127.0.0.1:%s" % frontend_port)
            socket.send ("[data-req] NEW DATA")
            #  Get the reply.
            message = socket.recv_multipart()
            data = message[0].split('[data-rep]')[1]
            data = json.loads(data)
            print("Last Measurement is : {}".format(data[-1]))
            return data[-1]
        except:
            return None

    def monitor(self, ):
        print("Starting monitoring process")
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        print("Collecting updates from server...")
        socket.connect ("tcp://127.0.0.1:%s" % self.monitor_port)
        socket.setsockopt(zmq.SUBSCRIBE, "")
        while True:
            string = socket.recv_multipart()

