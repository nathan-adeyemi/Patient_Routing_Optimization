import os
import glob
import datetime

from ray.rllib.algorithms.algorithm import Algorithm

def create_checkpoint(train_job: Algorithm, checkpoint_dir: str):
    dir_name = get_current_checkpoint() + 1
    dir_name = f'checkpoint_{dir_name}'
    train_job.save(checkpoint_dir)
    
    
def get_current_checkpoint(dir):
    return glob.glob(os.path.join(dir,'checkpoint_*'))

def create_checkpoint_dir(config):
    flat_date = dt.date.today().strftime("%m_%d_%Y")
    dir_name = f"{config.experiment_name}_{flat_date}"
    os.mkdir(os.path.join(config.results_dir,dir_name))
    
    