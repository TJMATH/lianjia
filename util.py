import requests
import yaml
import logging
import logging.handlers
import colorlog

from contants import *


def set_logger(log_filename = LOG_FILENAME):
    logger = logging.getLogger(name=log_filename)
    logger.setLevel(logging.DEBUG)
    
    log_color = {'DEBUG': 'bold_cyan', 'INFO': 'bold_green',
                'WARNING': 'bold_yellow', 'ERROR': 'bold_red',
                'CRITICAL': 'bg_white,bold_red'}
    formatter = colorlog.ColoredFormatter(
        '[%(yellow)s%(asctime)s%(reset)s - %(blue)s%(process)d-%(threadName)s%(reset)s - '
        '%(filename)s:%(lineno)d %(log_color)s%(levelname)s%(reset)s] %(message)s',
        # datefmt='%Y-%m-%d %H:%M:%S',
        log_colors=log_color)
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        log_filename, maxBytes=10485760, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = set_logger()

def get_cookies():
    """解析cookies内容并添加到cookiesJar"""
    manual_cookies = {}
    for item in COOKIE_STR.split(';'):
        name, value = item.strip().split('=', 1)
        # 用=号分割，分割1次
        manual_cookies[name] = value
        # 为字典cookies添加内容
    cookiesJar = requests.utils.cookiejar_from_dict(manual_cookies, cookiejar=None, overwrite=True)
    return cookiesJar

def get_session():
    # 初始化session
    session = requests.session()
    session.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36",
                       "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                       "Connection": "keep-alive"}
    # checksession = requests.session()
    # checksession.headers = {"User-Agent": global_config.getRaw('config', 'DEFAULT_USER_AGENT'),
    #                         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
    #                         "Connection": "keep-alive"}
    # 获取cookies保存到session
    session.cookies = get_cookies()
    return session