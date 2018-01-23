import time
import zmq_app
from multiprocessing import Process

ws = zmq_app.ZMQ_for_WeatherStation()
            
monitoring_p = Process(target=ws.monitordevice)
monitoring_p.start()  

server_p = Process(target=ws.server, args=(ws.backend_port,))
server_p.start()  

monitorclient_p = Process(target=ws.monitor)
monitorclient_p.start()  
time.sleep(2)   

# these two will drop when we start running with datalogger software at site and ATHENA
Process(target=ws.client_datalogger, args=(ws.frontend_port,)).start()
Process(target=ws.client_athena, args=(ws.frontend_port,)).start()

time.sleep(30)
server_p.terminate()
monitorclient_p.terminate()
monitoring_p.terminate()
