import sys
sys.path.append('src')

import ray
import gymnasium as gym
import hydra
import pkl
import matplotlib.pyplot as plt

from utils import dir_utils
from omegaconf import DictConfig
from .envs.test_bench_env import TestBenchEnv
from ray.rllib.algorithms.appo import APPOConfig
from ray.rllib.algorithms.algorithm import Algorithm

            
def train_fn(cfg: DictConfig):
    if not checkpoint_path is None:
        agent = build_agent(**cfg)
        agent = agent.build()
        dir_utils.create_checkpoint_dir(dir=cfg.experiment_info.results_dir)
        train_it=0
        reward_list=[]
    else:
        # Input code for grabbing the previously run agent 
        Algorithm.restore(checkpoint_path=checkpoint_path)
        with open(os.path.join(checkpoint_path,'results_list.pkl'),mode = 'rb') as f:
                reward_list = pkl.load(f)
                train_it = len(reward_list)-1


    while train_it < cfg.experiment_info.training.max_iterations:
        result=agent.train()
        mean_reward =
        reward_list.append(result['episode_reward_mean'])

        if train_it % cfg.experiment_info.eval.frequency == 0 or  result['episode_reward_mean'] > cfg.experiment_info.training.episode_reward_mean:

            # Perform policy evaluation and log results
            agent.evaluate()
            
            # Implement Agent and model checkpoint saving
            dir_utils.create_checkpoint(agent, checkpoint_path)
            with open(os.path.join(checkpoint_path,'results_list.pkl'),mode = 'wb') as f:
                pkl.dump(reward_list,f)
                
                
            # Training Progress Plotting (Improve with seaborn later)
            plt.plot(reward_list)
                
            # Logging
            print("Routing Agent Training Iteration {}:\nAverage Reward Incurred: {}".format(train_it+1, result['episode_reward_mean']))
            print('Agent Checkpoint information dir: {}'.format(checkpoint_path))
        
        # Temporary agent training termination criteria 
            if reward_list[-1] > cfg.experiment_info.training.episode_reward_mean: 
                print("Insert Termination Message")
                break

        train_it+=1
    agent.close()
        

def build_agent(experiment_info: DictConfig):
    agent_cfg=DictConfig(dict())
    agent_cfg.update({'_target_': experiment_info.target})
    agent_cfg.update(experiment_info=experiment_info)
    agent=hydra.utils.instantiate(agent_cfg,_recursive_=False)

    return agent

class appo_cfg(APPOConfig):
    def __init__(self,experiment_info: DictConfig,
                 hyper_params: DictConfig)-> None:
        super().__init__()
        self.training(lr=hyper_params.lr,
                    grad_clip=hyper_params.gc,
                    use_critic=experiment_info.training.vf_optim.separate_models,
                    vtrace=experiment_info.training.vf_optim.vtrace)
        self.rollouts(num_rollout_worker=experiment_info.num_workers)
        self.environment(env=TestBenchEnv,env_config=experiment_info.env.network_size)
        self.evaluation(evaluation_interval=experiment_info.eval.frequency,
                        evaluation_duration=experiment_info.eval.num_episodes,
                        evaluation_duration_unit=experiment_info.eval.units,
                        evaluatio_num_workers=experiment_info.eval.num_workers)
        
        

        
    

