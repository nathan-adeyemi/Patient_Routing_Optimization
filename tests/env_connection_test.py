import sys
sys.path.append('src')

import gymnasium as gym
import numpy as np
from envs import test_bench_env

if __name__ == "__main__":
    
    env = gym.make('mhSimulationEnvironment-v0',
                   size = 'Small',
                   path = 'src/envs/Simulations/simulation_trigger.sh',
                   debug = False)
    
    obs_list = []
    rew_list = []
    info_list= []
    
    obs, info = env.reset()
    
    while True:
        
        action = np.random.choice(range(3))
        obs, reward, terminated, truncated, info = env.step(action)
        
        obs_list.append(obs)
        rew_list.append(reward)
        info_list.append(info)
        
        if terminated or truncated:
            break
    
    remaining_rewards = env.clear_reward_buffer()
    remaining_rewards_ids = set([i['reward_patient_id'] for i in remaining_rewards])
    
    observation_ids = set([i['observation_patient_id'] for i in info_list])
    reward_ids = set([i['reward_patient_id'] for i in info_list])
    
    missing_reward_ids = observation_ids - reward_ids
    print(missing_reward_ids.remove('terminate') == remaining_rewards_ids)
    
    print('Env Trajectory Complete')