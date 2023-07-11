import subprocess
import sys
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'sagemaker', 'ray', 'modin[ray]', 'pydantic==1.10.10', 'xgboost_ray'])
import os
import time
import tarfile
import argparse
import json
import logging
import boto3
import sagemaker
import glob

import pathlib
import numpy as np
from math import sqrt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Sagemaker specific imports
from sagemaker.session import Session
from sagemaker.experiments.run import load_run
import modin.pandas as pd
# Ray specific imports
import ray
from ray.air.checkpoint import Checkpoint
from ray.train.xgboost import XGBoostCheckpoint, XGBoostPredictor
import ray.cloudpickle as cloudpickle

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

if __name__ == "__main__":
    logger.debug('Starting evaluation.')
    
    model_dir = '/opt/ml/processing/model/'
    for file in os.listdir(model_dir):
        logger.info(file)
    
    logger.debug('Loading model.')
    model_path = os.path.join(model_dir, 'model.tar.gz')
    # Open the .tar.gz file
    with tarfile.open(model_path, 'r:gz') as tar:
        # Extract all files to the model directory
        tar.extractall(path=model_dir)

    for file in os.listdir(model_dir):
        logger.debug(file)
                     
    # Load the serialized model data from a file
    with open(f'{model_dir}model.pkl', "rb") as f:
        serialized_model = f.read()

    # Deserialize the model using cloudpickle
    result = cloudpickle.loads(serialized_model)
    metrics = result.metrics

    # See the regression metrics
    # see: https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-model-quality-metrics.html
    logger.debug('extracting metrics.')
    mae = metrics['valid-mae']
    rmse = metrics['valid-rmse']
    report_dict = {
        'regression_metrics': {
            'mae': {
                'value': mae,
            },
            'rmse': {
                'value': rmse,
            },
        },
    }

    output_dir = '/opt/ml/processing/evaluation'
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.info('Writing out evaluation report with rmse: %f', rmse)
    evaluation_path = f'{output_dir}/evaluation.json'
    with open(evaluation_path, 'w') as f:
        f.write(json.dumps(report_dict))
