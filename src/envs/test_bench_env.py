import gymnasium as gym
import subprocess
import numpy as np
import pandas as pd
import socket
import os
import io

from gymnasium import spaces
from gymnasium.envs.registration import register
from utils.r_communication import find_available_port

register(id='mhSimulationEnvironment-v0',entry_point='envs.test_bench_env:TestbenchEnv')
# Simulation Environment Class that communicates with the R session to send actions 
# and receive state observations
class TestbenchEnv(gym.Env):
    def __init__(self,size,path: str, debug: bool = False):
        
        super().__init__()
        self.size = size
        self.sh_path = path
        
        if 'Small' in self.size:
            self.n_queues = 3
        elif self.size == 'Medium':
            self.n_queues=5
        else:
            self.n_queues = 10
            
        port = find_available_port(print_port = debug)
        
        # Create a socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to a specific address and port
        server_address = ('localhost', port)
        self.server.bind(server_address)
        
        
        if not debug:
       
            subprocess_env = os.environ.copy()
            subprocess_env['port'] = str(port)
            subprocess_env['size'] = str(self.size)
            
            try:
                self.process = subprocess.Popen(['bash', self.sh_path], env=subprocess_env)
            except Exception as e:
                print(f'Error starting the shell script: {e}') 
        
        
        # Listen for incoming connections
        self.server.listen(1)
        
        # # Accept the client connection
    
        self.client, _ = self.server.accept()
    
        # Set up server side port connection to transmit actions to the R simulation
                
        # Observations are dictionaries with the agent's and the target's location.
        # Each location is encoded as an element of {0, ..., `size`}^2, i.e. MultiDiscrete([size, size]).
        self.observation_space = spaces.Box(low = 0, high = 100.0, shape=(self.n_queues,), dtype=float)

        # Number of possible action is the number of queues
        self.action_space = spaces.Discrete(self.n_queues)
            
    def _receive_client_data(self, json_format = False):
        id = self.client.recv(1024).decode('utf-8')
        
        if json_format:
            self._send_client_data(data = 'ID received')
            info = self.client.recv(1024).decode('utf-8')
            if isinstance(info,str) and not info == 'terminate':
                info = eval(info)
            # Parse the received JSON data
            if isinstance(info,list):
                    info = info[0]
            try:
                if isinstance(info, int) or isinstance(info,float) or info == 'terminate':
                    pass
                elif info is None or info == 'None':
                    info = None
                else:
                    info = pd.read_json(io.StringIO(info))
                    info = self.format_observation(info)
            except ValueError or TypeError as e:   
                print(f"Error decoding JSON: {e}")
                 
            return info, id
        else:
            return id
    
    def _send_client_data(self,data):
        if not isinstance(data,bytes):
            data = data.encode()
        self.client.sendall(data)

    def reset(self, seed=None, options=None):
        
        # We need the following line to seed self.np_random
        super().reset(seed=seed)
        
        # Start running Simmer simulation and return obervation and info when the first routing decision is to be made
        signal = "intial_observation"
        self._send_client_data(signal)
        observation, id = self._receive_client_data(json_format=True)
        return observation, {'observation_patient_id': id}

    def step(self, action):
        
        # Tell the simulation which pool to route the entity to        
        action = str(action + 1)
        self._send_client_data(action)
        
        # TO-DO: Pass observation information in JSON format from the R simulation (for Minn. MH simulation)
        reward, rew_id = self._receive_client_data(json_format=True)  
        
        # An episode is done iff the agent has reached the target
        terminated = False
        if reward == 'terminate':
            terminated = True
            reward = None
            observation = None
        
        else:
            # Receive the state observation from the simulation
            observation, obs_id = self._receive_client_data(json_format =True)
            if isinstance(observation,str):
                if observation == 'terminate':
                    terminated = True
                    reward = None
                    observation = None
                

            info = {'observation_patient_id': obs_id, 'reward_patient_id': rew_id} 

        return observation, reward, terminated, False, info
    
    def terminate_env(self):
        # Close the sockets
        self.client_socket.close()
        self.self.server.close()
        
    def _gen_termination_data(self):
        data = pd.DataFrame(index=range(self.n_queues),columns = ["termination" for i in range(self.n_queues)])
        data.loc[0] = 'termination'
        return data
    
    
    def format_observation(self,obs):
        
        if not isinstance(obs,pd.DataFrame):
            obs = pd.DataFrame.from_records(obs)
        obs = obs.set_index(obs.iloc[:,0]).drop([list(obs.columns)[0]],axis=1).to_numpy().transpose()
        
        return obs
    
    def clear_reward_buffer(self):
        rew_list=[]
        while True:
            self._send_client_data('next_reward')
            reward, id = self._receive_client_data(json_format = True)
            
            if reward == 'terminate' or id == 'terminate':
                break
            else:
                rew_list.append({'reward_patient_id': id, 'reward': reward})
        
        return rew_list

        
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
        bracket_vals =  self.gamma * self.state_action_values[next_state][self.greedy_action(next_state)]
        bracket_vals = reward_val + bracket_vals - self.state_action_values[action_state]
        return self.state_action_values[action_state] + self.alpha * bracket_vals