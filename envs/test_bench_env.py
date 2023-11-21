import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import socket
import json

# Simulation Environment Class that communicates with the R session to send actions 
# and receive state observations
class TestbenchEnv(gym.Env):
    super().__init__
    def __init__(self,size):
       
        self.size = size
        if(port == None):
            port = find_available_port(print_port = True)
        
        # Create a socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to a specific address and port
        server_address = ('localhost', port)
        self.server.bind(server_address)
        
        # Listen for incoming connections
        self.server.listen(1)
        
        # Accept the client connection
        self.client, _ = self.server.accept()
    
    # Set up server side port connection to transmit actions to the R simulation
    
        self.client.sendall(self.size.encode())
        self.n_queues = self._receive_client_data(conv_float = True)
        self.n_queues = int(self.n_queues)
                
        # Observations are dictionaries with the agent's and the target's location.
        # Each location is encoded as an element of {0, ..., `size`}^2, i.e. MultiDiscrete([size, size]).
        self.observation_space = spaces.Box(low = 0, high = 100.0, shape=(self.n_queues,), dtype=float)

        # Number of possible action is the number of queues
        self.action_space = spaces.Discrete(self.n_queues)
            
    def _receive_client_data(self, json_format = False):
        info = self.client.recv(1024).decode('utf-8')

        if json_format:
            # Parse the received JSON data
            try:
                info = pd.DataFrame(json.loads(info))
                if 'terminate' in info.columns:
                    id = 'termination message'
                else:
                    id = info['id']
                    info = info.drop(columns=['id'])
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
            return info, id
        else:
            return info
    
    def _send_client_data(self,data):
        self.client.sendall(data.encode())

    def reset(self, seed=None, options=None):
        
        # Send a simulation initiation message to the simulation thread
        signal = 'x'
        self._send_client_data(signal)
        
        # We need the following line to seed self.np_random
        super().reset(seed=seed)
        
        # Start running Simmer simulation and return obervation and info when the first routing decision is to be made
        _ = self._receive_client_data()
        signal = "intial_observation"
        self._send_client_data(signal)
        observation, id = self._receive_client_data(json_format=True)
        return observation, {'observation_patient_id': id}

    def step(self, action):
        
        # Tell the simulation which pool to route the entity to        
        action = str(action + 1)
        self._send_client_data(action)
        
        # Receive the state observation from the simulation
        observation, obs_id = self._receive_client_data(json_format=True)
        
        # An episode is done iff the agent has reached the target
        terminated = False
        if 'terminate' in obs_id:
            terminated = True
            reward = None
            observation = None
            info={}
        else:

            # TO-DO: Pass observation information in JSON format from the R simulation (for Minn. MH simulation)
            self._send_client_data('reward signal')
            reward, rew_id = self._receive_client_data(json_format=True)
            
            # TO-DO: Parse a sample ID from the observation and the received reward in the 
            # Then use the sample IDs to correctly link observations and 
            # rewards before performing model weight updates. 
            # Reason: An action's reward is not immediately available when the next
            # action needs to be executed which ruins the order samples are processed 
            # during policy weight updates. We need to properly link rewards and actions before 
            # training the actor and critic models

            # Sequence

            # 1. Receive observation and unique ID in JSON format
            # 2. Send reward signal
            # 3. Reward signal:
            #         - if no reward is available return NULL
            #         - else return patient ID and TTP as reward in JSON format

            info = {'observation_patient_id': obs_id, 'reward_patient_id': rew_id} 

        return observation, reward, terminated, info
    
    def terminate_env(self):
        # Close the sockets
        self.client_socket.close()
        self.self.server.close()
        
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
        
# Agent class to choose actions and synthesize state information
class qRoutingAgent():
    
    def __init__(self,n_queues,num_states = 10,alpha = 0.1, epsilon = 0.9):
        # Class initiation
        self.n_queues = n_queues
        self.num_states = num_states
        self.action_space = np.linspace(start = 1, stop = n_queues,num = n_queues)
        self.rng = np.random.default_rng()
        self.epsilon = epsilon
        self.alpha = alpha
        # Testbed Q-Table 
            # First n indices are the states for each of the n queues
            # Final index is for the action 
        self.state_action_values = np.zeros(shape = (self.num_states,self.num_states,self.num_states,self.n_queues))
        
    def epsilon_greedy(self, current_state):
        if self.rng.random() < self.epsilon:
            return self.random_sample()
        else:
            return self.greedy_action(current_state)
        
    def update_table(self,current_state, action_taken, state_observed, reward_received):
        # Index states according to the utilization bins
        action_state_index =  self.bin_states(current_state) +  (int(action_taken),)
        print(action_state_index)
        ipdb.set_trace()
        observed_state = self.bin_states(state_observed)
        
        # Assign the discounted reward value to the table index
        self.state_action_values[action_state_index] = self.discount_reward(action_state_index,observed_state,reward_received)
        
    # Randomly choose an action from the action space    
    def random_sample(self):
        return self.rng.integers(low = 1,high = self.n_queues, size = 1)
    
    # Select action according to a greedy policy
    def greedy_action(self,current_state):
        current_state = self.bin_states(current_state)
        return np.argmax(self.state_action_values[current_state])
    
    # Bins the continuous state value to a table index
    def bin_states(self, state):
        return tuple([int(np.max(np.where(float(i) > np.linspace(0,100,self.num_states)))) for i in state])
    
    def discount_reward(self,action_state,next_state,reward_val):
        ipdb.set_trace()
        bracket_vals =  self.gamma * self.state_action_values[next_state][self.greedy_action(next_state)]
        bracket_vals = reward_val + bracket_vals - self.state_action_values[action_state]
        return self.state_action_values[action_state] + self.alpha * bracket_vals