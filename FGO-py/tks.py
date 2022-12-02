import yaml
import sys
from fgoConst import VERSION
import fgoDevice
import fgoLogging
import fgoSchedule


with open('tksConfig.yaml', "r", encoding="utf-8") as f:
    tksConfig = yaml.load(f, Loader=yaml.FullLoader)

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
