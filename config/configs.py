import yaml
import json
import sys

sys.path.append('..')
from src.utils import DDict
from util import logger


class Configure(DDict):
    def __init__(self, configPath: str = None, *args, **kwargs) -> None:
        self.configPath = "config.yml"
        if configPath:
            self.configPath = configPath
        logger.info(f"加载配置: {self.configPath}...")
        with open(self.configPath, 'r', encoding='utf-8') as fin:
            config = yaml.load(fin, Loader=yaml.FullLoader)
        super().__init__(config)
        logger.info(f"[任务类型] {self.type}")
        logger.info(f"[输出目录] {self.outputDir}")
        logger.info(f"[具体配置]\n{json.dumps(self[self.type], indent = 2)}")
        logger.info("配置加载完毕!")
