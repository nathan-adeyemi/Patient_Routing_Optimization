# Agent  class to choose actions and synthesize state information
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