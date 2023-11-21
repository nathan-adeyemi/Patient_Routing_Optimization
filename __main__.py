import hydra
import ray

from agent_utils import build_agent
from omegaconf import DictConfig

@hydra.main(config_path='experiment_configs', config_name='inverted_V_testbench')

def train_fn(cfg: DictConfig):
    agent=build_agent(**cfg)
    train_it=0
    reward_list=[]

    while train_it < cfg.experiment_info.training.max_iterations:
        result=agent.train()
        reward_list.append(result['episode_reward_mean'])

        if train_it % cfg.experiment_info.eval.interval == 0:

            # Perform policy evaluation and log results
            agent.evaluate()
            # Insert logging code

            # Implement Agent and model checkpoint saving
            checkpoint_path = agent.save().checkpoint.path
            print('Agent Checkpoint information dir: {}'.format(checkpoint_path))
            pass

        
        # Temporary agent training termination criteria 
        if reward_list[-1] > cfg.experiment_info.training.episode_reward_mean: 
            print("Insert Termination Message")
            break

        train_it+=1
    agent.close()

if __name__ == '__main__':

    ray.init()
    train_fn()
    ray.shutdown()
