import hydra
import ray

from agent_utils import build_agent
from omegaconf import DictConfig

@hydra.main(config_path='experiment_configs', config_name='inverted_V_testbench')
if __name__ == '__main__':
    
    ray.init()
    train_fn()
    ray.shutdown()