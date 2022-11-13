import yaml


class TksConfig:
    def __init__(self, file='tksConfig.yaml'):
        with open(file, "r", encoding="utf-8") as f:
            self.data = yaml.load(f, Loader=yaml.FullLoader)
