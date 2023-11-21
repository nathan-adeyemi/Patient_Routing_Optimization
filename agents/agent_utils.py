import ray
import gymnasium as gym
import hydra

from omegacong import DictConfig
from .envs.test_bench_env import TestBenchEnv
from ray.rllib.algorithms.appo import APPOConfig

def build_agent(experiment_info: DictConfig):
    agent_cfg=DictConfig(dict())
    agent_cfg.update({'_target_': experiment_info.target})
    agent_cfg.update(experiment_info=experiment_info)
    agent=hydra.utils.instantiate(agent_cfg,_recursive_=False)

    return agent

class appo_cfg(APPOConfig):
    def __init__(self,experiment_info: DictConfig)-> None:
        super().__init__()
        self.training(lr=experiment_info.hyper_params.lr,
                    grad_clip=experiment_info.hyper_params.gc,
                    use_critic=experiment_info.training.vf_optim.separate_models,
                    vtrace=experiment_info.training.vf_optim.vtrace)
        self.rollouts(num_rollout_worker=experiment_info.num_workers)
        self.environment(env=TestBenchEnv,env_config=experiment_info.env.queuing_network_size)
        self.evaluation(evaluation_interval=experiment_info.eval.interval,
                        evaluation_duration=experiment_info.eval.num_episodes,
                        evaluation_duration_unit=experiment_info.eval.units,
                        evaluatio_num_workers=experiment_info.eval.num_workers)
        
    

