import re
import sys

sys.path.append('..')
from src.utils import DDict
from contants import HOST
from util import logger

class DataBase():
    def __init__(self, url):
        self.host = HOST
        self.url = url

    def _toStr(self, s, suffix = '\t'):
        if isinstance(s, str):
            return s.strip().replace('\t', '    ') + suffix
        return str(s) + suffix

class House(DataBase):
    """
        'app_source',
        'app_source_brand',
        'bedroom_num',
        'city_id',
        'contact_ucid',
        'frame_hall_num',
        'hdic_bizcircle_id',
        'hdic_resblock_id',
        'houseCode',
        'houseCondition',
        'name',
        'needLogin',
        'offline',
        'pageId',
        'pcsource',
        'rent_price',
        'rent_type',
        'subway',
        'use_pc_duty_info'
    """
    def __init__(self, url) -> None:
        super().__init__(url)
        self.houseBaseInfo = DDict()
        self.houseCode = url.strip('/').split('/')[-1][:-5]
        self.done = False
        self.subway = []

    def _load_house_base_info_from_soup(self, soup):
        baseInfo = soup.select("#info > ul:nth-child(2)")
        if len(baseInfo) == 0:
            logger.error(f"无法获取房屋基本信息: {self.houseCode}")
            return False
        baseInfo = baseInfo[0].find_all('li')
        baseInfoDict = DDict()
        for bi in baseInfo:
            content = bi.text
            if "：" in content:
                k, v = content.split("：")
                baseInfoDict[k.strip()] = v.strip()
        if not baseInfoDict:
            logger.error(f"无法获取房屋基本信息: {self.houseCode}")
            return False
        self.houseBaseInfo = baseInfoDict
        return True

    def _load_g_conf_from_soup(self, soup):
        scripts = soup.find_all('script')
        for t in scripts:
            if "g_conf.hdic_resblock_id =" in t.text:
                break
        g_conf = self
        for i, cmd in enumerate(re.findall('g_conf.+?;', t.text)):
            exec(cmd[:-1])
        # if len(self.subway) == 0:
        #     self._get_subways_from_soup(soup)
        return i > 0

    def load_from_soup(self, soup):
        if not self._load_g_conf_from_soup(soup):
            logger.error(f"加载房屋数据失败: {soup.find('title')}")
            # logger.debug(f"加载房屋数据失败: {soup}")
        elif self._load_house_base_info_from_soup(soup):
            self.done = True

    @property
    def house_url(self):
        return self.host + f'zufang/{self.houseCode}.html'
    
    @property
    def xiaoqu(self):
        return self.host + f"xiaoqu/{self.hdic_resblock_id}"

    @property
    def xiaoqu_zaizu(self):
        return self.host + f"zufang/c{self.hdic_resblock_id}"

    @property
    def header(self):
        header = [
            "小区名", "室", "厅", "面积", "租金", "朝向", "电梯", "用水", "用电", "楼层", "燃气", "周边地铁数量", "最近地铁距离", "最近地铁站", "到地铁站距离", "房屋链接"
        ]
        return '\t'.join(header)

    @property
    def String(self):
        """
        小区名, 室, 厅, 面积, 租金, 朝向, 电梯, 用水, 用电, 楼层, 燃气, 周边地铁数量, 最近地铁距离, 最近地铁站, 到地铁站距离, 房屋链接
        """
        string = self._toStr(self.name)
        string += self._toStr(self.bedroom_num)
        string += self._toStr(self.frame_hall_num)
        string += self._toStr(self.houseBaseInfo.get("面积", "暂无数据"))
        string += self._toStr(self.rent_price)
        string += self._toStr(self.houseBaseInfo.get("朝向", "暂无数据"))
        string += self._toStr(self.houseBaseInfo.get("电梯", "暂无数据"))
        string += self._toStr(self.houseBaseInfo.get("用水", "暂无数据"))
        string += self._toStr(self.houseBaseInfo.get("用电", "暂无数据"))
        string += self._toStr(self.houseBaseInfo.get("楼层", "暂无数据"))
        string += self._toStr(self.houseBaseInfo.get("燃气", "暂无数据"))
        string += self._toStr(len(self.subway))
        subways = sorted(self.subway, key=lambda x: x['distance'])
        if subways:
            string += f"{subways[0]['distance']}\t{self._toStr(subways[0]['name'], '')} - {self._toStr('/'.join(subways[0]['lines']))}"
            for i, subway in enumerate(subways):
                string += f"{subway['distance']}m - {self._toStr(subway['name'], '')} - {self._toStr('/'.join(subway['lines']), '')}"
                if i < len(subways) - 1:
                    string += ' && '
                else:
                    string += '\t'
        else:
            string += '\t\t\t'
        # string += self._toStr(self.xiaoquBaseInfo.get("建筑年代", "暂无数据"))
        string += self._toStr(self.house_url, '')
        # string += self._toStr(self.xiaoqu, '\n')
        return string


class Xiaoqu(DataBase):
    def __init__(self, url):
        super().__init__(url)
        self.xiaoquCode = url.strip('/').split('/')[-1]
        self.oneHouse = None
        self.xiaoquBaseInfo = DDict()
    
    @property
    def done(self):
        return len(self.xiaoquBaseInfo) > 0 and self.oneHouse is not None
    
    def load_xiaoqu_info_from_soup(self, soup):
        title = soup.find('h1', attrs = {'class': 'detailTitle'})
        if title:
            self.name = title.text.strip()
        else:
            logger.error(f"无法获取小区名 {self.url}")
            return False
        baseInfo = soup.find_all('div', attrs={"class": "xiaoquInfoItem"})
        baseInfoDict = DDict()
        for bi in baseInfo:
            k = bi.find(attrs = "xiaoquInfoLabel").text.strip()
            v = bi.find(attrs = "xiaoquInfoContent").text.strip()
            baseInfoDict[k] = v
        if not baseInfoDict:
            logger.error(f"无法获取小区基本信息: {self.name}")
            logger.debug(soup)
            return False
        self.xiaoquBaseInfo = baseInfoDict
        return True

    @property
    def subway(self):
        if self.oneHouse is None:
            return None
        return self.oneHouse.subway

    @property
    def zaizu(self):
        return self.host + f"zufang/c{self.xiaoquCode}"

    @property
    def halfHeader(self):
        return "建筑年代\t小区链接"

    @property
    def halfString(self):
        string = self._toStr(self.xiaoquBaseInfo.get("建筑年代", "暂无数据")) + self.url
        return string

    @property
    def header(self):
        return '小区名\t' + '\t'.join(self.oneHouse.header.split('\t')[11:15]) + '\t' + self.halfHeader

    @property
    def String(self):
        return self.name + '\t' + '\t'.join(self.oneHouse.String.split('\t')[11:15]) + '\t' + self.halfString