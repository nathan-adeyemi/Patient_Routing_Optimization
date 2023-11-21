import importlib
import rpy2
import envs
from rpy2 import robjects
import socket
import threading
import ipdb

importlib.reload(rl_classes)    

def runRLTask(port = None,nRep = 1):
    serverList = []
    clientList = []
    clientAddressList = []
    
    for i in range(0,nRep)
        # Identify an available port on the local host
        if(port == None):
            port = find_available_port(print_port = True)
        
        # Create a socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to a specific address and port
        server_address = ('localhost', port)
        server_socket.bind(server_address)
        
        # Listen for incoming connections
        server_socket.listen(1)
        
        # Accept the client connection
        client_socket, client_address = server_socket.accept()
        clientList.append(client_socket)
        clientAddressList.append(client_address)
        serverList.append(server_socket)

    
# Function to find an available port
def find_available_port(print_port = False):
    # Create a socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind to a random port
    s.bind(('localhost', 0))

    # Get the actual port number
    _, port = s.getsockname()

    # Close the socket
    s.close()
    
    if(print_port):
        print(port)

    return port

def simulation(port = None):
    
    # Load in all R libraries and connect the client socket end to the server
    robjects.r['source']('.Rprofile')
    
    # Pass testbed network setup the the simulation
    if(port == None):
        robjects.globalenv['port_val'] = port
        
    robjects.r['source']('Simulations/Test_Bed_Opt_Setup.R')
    
    # Simulation will begin executing when the begin signal is transmitted by the environment class
    

# connection_port = find_available_port()
    
# thread1 = threading.Thread(target = qRoutingAgent, kwargs= {"port": "connection_port",})
# thread2 = threading.Thread(target = simulation, kwargs = {"port": "connection_port",})

# thread1.start()
# thread2.start()        

# thread1.join()
# thread2.join()