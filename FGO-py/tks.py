import yaml
import argparse,os,sys
from fgoConst import VERSION
import fgoDevice
import fgoLogging
import fgoSchedule

# Load base config
with open('tksConfigBase.yaml', "r", encoding="utf-8") as f:
    tksConfig_base = yaml.load(f, Loader=yaml.FullLoader)

# Load user config
with open('tksConfig.yaml', "r", encoding="utf-8") as f:
    tksConfig = yaml.load(f, Loader=yaml.FullLoader)

# Merge configs: user config overrides base config
def merge_dicts(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            merge_dicts(base[k], v)
        else:
            base[k] = v
    return base

tksConfig = merge_dicts(tksConfig_base, tksConfig)

args = sys.argv[1:]

if 'loggerLevel' in tksConfig:
    fgoLogging.logger.handlers[-1].setLevel(tksConfig['loggerLevel'])
    fgoLogging.logger.root.handlers[-1].setLevel(tksConfig['loggerLevel'])

if 'device' in tksConfig:
    fgoDevice.device = fgoDevice.Device(tksConfig['device'])

if 'speed' in tksConfig:
    fgoSchedule.Schedule.speed = tksConfig['speed']

from tksMain import TksMain
TksMain(args, tksConfig)()
