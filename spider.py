import requests
from bs4 import BeautifulSoup
from requests import RequestException
from urllib.parse import urlencode
import json
import re
from config import *
import pymongo
import os
from hashlib import md5
from multiprocessing import Pool
from json.decoder import JSONDecodeError


client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]

def get_page_index(offset,keyword):
    """
    请求今日头条街拍数据
    :param offset:
    :param keyword:
    :return:
    """
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': 20,
        'cur_tab': 3,
        'from': 'gallery'
    }
    headers = {
        'User-Agent': "Mozilla / 5.0(Windows NT 10.0;Win64;x64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 93.0.3239.108Safari / 537.36"
    }
    url = "https://www.toutiao.com/search_content/?"+urlencode(data)
    try:
        response = requests.get(url,headers=headers)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print("请求索引出错了！")
        return None

def parse_page_index(html):
    """
    生成器返回妹子图片url
    :param html:
    :return:
    """
    try:
        data = json.loads(html)
        if data and "data" in data.keys():
            for item in data.get("data"):
                if item and "article_url" in item.keys():
                    yield item.get("article_url")
    except JSONDecodeError:
        pass


def get_page_detail(url):
    """
    获取详情页信息
    :param url:
    :return:
    """
    request = requests.session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'
         #'Remote Address': '153.3.235.87:443',
         #'Referrer Policy': 'no - referrer - when - downgrade'
    }
    cookies = {
        "cookies":"tt_webid=6628483263928075784; UM_distinctid=16754af71e25-03ff22c46af1bb-8383268-1fa400-16754af71e35d2"
    }

    try:
        # redirection = request.head(url,allow_redirects=True)
        # response = request.get(redirection.url,allow_redirects=False, headers=headers)
        # url = response.headers['location']
        # print(url)
        # resp = request.get(url,cookies=cookies)
        resp = requests.get(url,headers=headers,cookies=cookies)
        if resp.status_code == 200:
            return resp.text
        return None
    except RequestException:
        print("请求索引出错了！")
        return None

def parse_page_detail(html,url):
    """
    获取标签内容
    :param html:
    :param url:
    :return:
    """
    soup = BeautifulSoup(html,"lxml")
    title = soup.select("title")[0].get_text()
    image_pattern = re.compile('gallery: JSON.parse\("(.*?)"\),', re.S)
    result = re.search(image_pattern,html)
    if result:
        result = result.group(1).replace("\\", "")
        data = json.loads(result)
        if data and "sub_images" in data.keys():
            sub_images = data.get("sub_images")
            images = [item.get("url") for item in sub_images]
            for img in images: download_image(img)
            return {
                "title":title,
                "utl":url,
                "images":images
            }



def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print("存储到mongodb")
        return True
    else:
        return False

def download_image(url):
    try:
        print("正在下载",url)
        response = requests.get(url)
        if response.status_code == 200:
            save_to_image(response.content)
        return None
    except RequestException:
        print("请求图片出错了",url)
        return None

def save_to_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(),md5(content).hexdigest(),"jpg")
    if not os._exists(file_path):
        with open(file_path,"wb") as f:
            f.write(content)
            f.close()

def main(offset):
    html = get_page_index(offset,KEYWORD)
    for url in parse_page_index(html):
        html = get_page_detail(url)
        if html:
            result = parse_page_detail(html,url)
            print("data:    %s"%result)
            if result: save_to_mongo(result)


if __name__ == '__main__':
    groups = [x * 20 for x in range(GROUP_START,GROUP_END+1)]
    pool = Pool()
    pool.map(main,groups)
