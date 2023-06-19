import importlib
import testbed_classes as rl_classes
import rpy2
from rpy2 import robjects
import socket
import threading
import ipdb

importlib.reload(rl_classes)    

def runRLTask(port = None):
    
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
    
    env = rl_classes.TestbenchEnv(size = 'Small', server = server_socket, client = client_socket)
    routingAgent = rl_classes.qRoutingAgent(env.size)
        
    observation = env.reset(seed=42)
    reward_total = 0

    for _ in range(1000):
        
        prev_observation = observation
        current_action = routingAgent.epsilon_greedy(prev_observation)
        observation, reward, terminated = env.step(current_action)
        routingAgent.update_table(current_state=prev_observation,
                                  action_taken=current_action,
                                  state_observed=observation,
                                  reward_received=reward)
        
        if terminated:
            observation = env.reset()

    env.close()
    
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