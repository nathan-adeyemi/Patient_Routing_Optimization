from gym.envs.registration import register
from .test_bench_env import TestbenchEnv, TestbenchEnvVec

register(id='mhSimulationEnvironment-v0',entry_point='envs.test_bench_env:TestbenchEnv')
# register(id='mhSimulationEnvironmentVec_v0',entry_point='envs.test_bench_env:TestbenchEnv')