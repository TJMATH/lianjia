import os
import sys
import re
import time
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import List

from util import get_session, logger
from src.utils import DDict
from data.datas import House, Xiaoqu
from config.configs import Configure
from contants import *


class SpiderFactory():
    def __init__(self, configPath: str = None) -> None:
        self.config = Configure(configPath)
        self.spiderDict = {
            'house': HouseSpider,
            'xiaoqu': XiaoquSpider,
            'condition': None
        }

    def gen_worker(self):
        return self.spiderDict[self.config.type](self.config)

class BaseSpider():
    def __init__(self, config) -> None:
        self.session = get_session()
        self.config = config
        self.store = DDict({
            "houses": DDict(),             # {houseCode: house}
            "xiaoqus": DDict()             # {xiaoquCOde: xiaoqu}
        })
        options = webdriver.ChromeOptions()
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36")
        options.add_argument("blink-settings=imagesEnabled=false")
        options.add_argument("--disable-extensions")
        options.add_argument('-ignore -ssl-errors')
        options.add_argument('headless')
        options.add_argument('-ignore-certificate-errors')
        options.add_experimental_option("excludeSwitches", ['enable-automation','enable-logging'])
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(2)
        self.wait = WebDriverWait(self.driver, 2)
        if not os.path.exists(self.config.outputDir):
            os.makedirs(self.config.outputDir, exist_ok=True)

    def _load_one_page(self, url):
        resp = self.session.get(url)
        if resp.status_code != requests.codes.OK:
            logger.info(f"访问失败:  {url}")
            return False
        return BeautifulSoup(resp.text, features="lxml")

    def _close_tanchuang(self):
        try:
            self.driver.find_element(By.CLASS_NAME, "notice-close").click()
            return True
        except:
            return False

    def _get_subways_from_url(self, url):
        self.driver.get(url)
        tanchuang = self._close_tanchuang()
        contentMap = self.driver.find_element(By.CLASS_NAME, "content__map")
        if not tanchuang:
            tanchuang = self._close_tanchuang()
        self.driver.execute_script("arguments[0].scrollIntoView(true)", contentMap)
        time.sleep(2)
        if not tanchuang:
            tanchuang = self._close_tanchuang()
        soup = BeautifulSoup(self.driver.page_source, features="lxml")
        tags = soup.find_all('ul', attrs={'class': 'content__map--overlay__list'})[0].find_all('li')
        subways = []
        for tag in tags:
            subway = {}
            ps = tag.find_all('p')
            if len(ps) < 2:
                break
            subway['name'] = ps[0].text
            subway['distance'] = ps[0].span.text[:-1]
            subway['lines'] = ps[1].text.split(';')
            subways.append(subway)
        # logger.info(subways)
        return subways

    def load_house(self, url):
        house = House(url)
        if house.houseCode in self.store.houses:
            return self.store.houses[house.houseCode]
        house_soup = self._load_one_page(url)
        if not house_soup:
            return house
        house.load_from_soup(house_soup)
        if len(house.subway) == 0:
            if self.store.xiaoqus.get(house.hdic_resblock_id) is not None:
                house.subway = self.store.xiaoqus[house.hdic_resblock_id].subway
            else:
                house.subway = self._get_subways_from_url(house.url)
        return house

    def load_xiaoqu(self, url: str = None):
        xiaoqu = Xiaoqu(url)
        if xiaoqu.xiaoquCode in self.store.xiaoqus:
            return self.store.xiaoqus[xiaoqu.xiaoquCode]
        xiaoqu_soup = self._load_one_page(url)
        if not xiaoqu_soup:
            return xiaoqu
        xiaoqu.load_xiaoqu_info_from_soup(xiaoqu_soup)
        return xiaoqu

    def parse_house_urls(self, soup):
        urlTags = soup.find_all('a', attrs={'class': 'content__list--item--aside'})
        if len(urlTags) == 0:
            logger.info("未能获取到房屋信息")
            return []
        return [HOST + tag.attrs['href'][1:] for tag in urlTags]

    def get_zaizu_house_urls(self, zaizu_url: str) -> List:
        soup = self._load_one_page(zaizu_url)
        urls = []
        if soup:
            urls = self.parse_house_urls(soup)
        return urls

    def load_one_house(self, xiaoqu: Xiaoqu):
        pass

    def read_urls(self):
        pass

    @property
    def xiaoqu_filename(self):
        return os.path.join(self.config.outputDir, 'xiaoqu.tsv')

    @property
    def house_filename(self):
        return os.path.join(self.config.outputDir, 'house.tsv')

    # def __del__(self):
    #     self.fout.close()



class HouseSpider(BaseSpider):
    def read_urls(self):
        assert os.path.exists(self.config.house.inputFile), f"文件不存在: {self.config.house.inputFile}"
        urls = []
        with open(self.config.house.inputFile, 'r') as fin:
            for line in fin:
                urls.append(line.strip())
        return urls

    def run(self):
        fout_house = open(self.house_filename, 'w')
        fout_xiaoqu = open(self.xiaoqu_filename, 'w')
        houseHeader = None
        xiaoquHeader = None
        urls = self.read_urls()
        for url in tqdm(urls):
            houseLine = ""
            xiaoquLine = ""
            house = self.load_house(url)
            if house.done and house.houseCode not in self.store.houses:
                houseLine += house.String
            else:
                continue
            xiaoqu = self.load_xiaoqu(house.xiaoqu)
            if xiaoqu.oneHouse is None:
                xiaoqu.oneHouse = house
            if not xiaoqu.done:
                continue
            if houseHeader is None:
                houseHeader = house.header + '\t' + xiaoqu.halfHeader + '\n'
                fout_house.write(houseHeader)
            if xiaoquHeader is None:
                xiaoquHeader = xiaoqu.header + '\n'
                fout_xiaoqu.write(xiaoquHeader)
            houseLine += '\t' + xiaoqu.halfString + '\n'
            fout_house.write(houseLine)
            self.store.houses[house.houseCode] = house
            if xiaoqu.xiaoquCode not in self.store.xiaoqus:
                xiaoquLine = xiaoqu.String + '\n'
                fout_xiaoqu.write(xiaoquLine)
                self.store.xiaoqus[xiaoqu.xiaoquCode] = xiaoqu

        fout_house.close()
        fout_xiaoqu.close()
        self.driver.close()


class XiaoquSpider(BaseSpider):
    def read_urls(self):
        assert os.path.exists(self.config.xiaoqu.inputFile), f"文件不存在: {self.config.xiaoqu.inputFile}"
        xiaoqus = []
        with open(self.config.xiaoqu.inputFile, 'r', encoding="utf-8") as fin:
            for line in fin:
                xiaoqus.append(line.strip())
        urls = []
        for xq in xiaoqus:
            urls.extend(self.get_zaizu_house_urls(f"{HOST}zufang/rs{xq}"))
        # print(urls)
        return urls

    def run(self):
        fout_house = open(self.house_filename, 'w')
        fout_xiaoqu = open(self.xiaoqu_filename, 'w')
        houseHeader = None
        xiaoquHeader = None
        urls = self.read_urls()
        for url in tqdm(urls):
            houseLine = ""
            xiaoquLine = ""
            house = self.load_house(url)
            if house.done and house.houseCode not in self.store.houses:
                houseLine += house.String
            else:
                continue
            xiaoqu = self.load_xiaoqu(house.xiaoqu)
            if xiaoqu.oneHouse is None:
                xiaoqu.oneHouse = house
            if not xiaoqu.done:
                continue
            if houseHeader is None:
                houseHeader = house.header + '\t' + xiaoqu.halfHeader + '\n'
                fout_house.write(houseHeader)
            if xiaoquHeader is None:
                xiaoquHeader = xiaoqu.header + '\n'
                fout_xiaoqu.write(xiaoquHeader)
            houseLine += '\t' + xiaoqu.halfString + '\n'
            fout_house.write(houseLine)
            self.store.houses[house.houseCode] = house
            if xiaoqu.xiaoquCode not in self.store.xiaoqus:
                xiaoquLine = xiaoqu.String + '\n'
                fout_xiaoqu.write(xiaoquLine)
                self.store.xiaoqus[xiaoqu.xiaoquCode] = xiaoqu

        fout_house.close()
        fout_xiaoqu.close()
        self.driver.close()