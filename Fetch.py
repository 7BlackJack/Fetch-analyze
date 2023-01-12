import json
import os
import requests
import time
from multiprocessing import Pool
import queue
import math
import csv
import pandas as pd
from flask import Flask, render_template, request


app = Flask(__name__)

headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': 'http://www.xinfadi.com.cn',
    'Proxy-Connection': 'keep-alive',
    'Referer': 'http://www.xinfadi.com.cn/priceDetail.html',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}


def get_count(start, end):
    data = {
        'limit': '20',
        'current': '1',
        'pubDateStartTime': '{}'.format(start),
        'pubDateEndTime': '{}'.format(end),
        # 'pubDateStartTime': '2022/12/25',
        # 'pubDateEndTime': '2022/12/26',
        'prodPcatid': '',
        'prodCatid': '',
        'prodName': '',
    }
    res = requests.post('http://www.xinfadi.com.cn/getPriceData.html',
                        headers=headers, data=data, verify=False)
    count = json.loads(res.text)['count']
    return count


def saved_data(data_lists, file):
    f = open(file, 'w', encoding='utf-8', newline='')
    if os.path.exists(file):
        f.truncate()
    header = ['一级分类', '品名', '最低价', '最高价', '平均价', '产地', '单位', '发布日期']
    csv_writer = csv.writer(f)
    csv_writer.writerow(header)
    for page_data in data_lists:
        for data in page_data:
            csv_writer.writerow(data)
    f.close()
    print('数据存储完成')


def crawl(index, start, end):
    data_lists = []
    data = {
        'limit': '20',
        'current': f'{index}',
        'pubDateStartTime': '{}'.format(start),
        'pubDateEndTime': '{}'.format(end),
        # 'pubDateStartTime': '2022/12/25',
        # 'pubDateEndTime': '2022/12/26',
        'prodPcatid': '',
        'prodCatid': '',
        'prodName': '',
    }

    res = requests.post('http://www.xinfadi.com.cn/getPriceData.html',
                        headers=headers, data=data, verify=False)
    print(f'{res.url}请求已发送')
    res_con = json.loads(res.text)
    dish_list = res_con['list']
    for i in dish_list:
        prodCat = i['prodCat']  # 一级分类
        prodName = i['prodName']  # 品名
        lowPrice = i['lowPrice']  # 最低价
        highPrice = i['highPrice']  # 最高价
        avgPrice = i['avgPrice']  # 平均价
        place = i['place']  # 产地
        unitInfo = i['unitInfo']  # 单位
        pubDate = i['pubDate'].split(' ')[0]  # 发布日期
        row = [prodCat, prodName, lowPrice, highPrice,
               avgPrice, place, unitInfo, pubDate]
        data_lists.append(row)
    print('一页数据被抓取')

    return data_lists


def crawl_data(file_name, start, end):

    startTime = start
    EndTime = end
    count = get_count(startTime, EndTime)
    # 获取总数据条
    # count = get_count()
    # 获取页数
    limit = math.ceil(count / 20)
    # 用于存储所有已解析的数据的容器
    data_queue = queue.Queue()
    pool = Pool()
    print('多进程并发已就绪...')
    for i in range(limit):
        # main(i+1)
        # 多进程抓取数据并回调返回每一页的数据
        pool.apply_async(crawl, args=(i + 1, startTime,
                         EndTime), callback=data_queue.put)
    pool.close()
    pool.join()
    # 用于存储所有页面数据的容器
    data_lists = []
    while not data_queue.empty():
        # 一页一页的数据
        data = data_queue.get()
        data_lists.append(data)
    # 把所有页面的数据全部存储到文件中
    saved_data(data_lists, file_name)


def save_dataOne(df):
    #  品种分布
    typeSum_count = df['一级分类'].value_counts()
    typeSum_count.to_csv('品种分布数据.csv')
    print('品种分布数据清洗已完成')


def save_dataTwe(df):

    # 均价平均价
    group = df.groupby('品名')['平均价'].mean().round(2)
    group.to_csv('均价平均价数据.csv')
    print('均价平均价数据清理已完成')


def brushone(item):
    # 把每一个省份名字进行处理
    datalist = list(item)
    for i in datalist:
        # print(i)
        return i


def save_dataThree(df):

    values_to_remove = ['网', '吊', '国产']
    # 删除特定无效数据
    df = df.loc[~df['产地'].isin(values_to_remove)]

    data = df['产地'].dropna(axis=0)
    data[2] = data.map(brushone)
    # 拆分省份
    data = data[2].value_counts()
    data.to_csv("省份数据.csv")
    print('省份数据数据清理已完成')


def brush_data(file):
    # 引入数据
    df = pd.read_csv('data_csv.csv')
    # 清洗数据并存储有效的统计数据
    save_dataOne(df)
    save_dataTwe(df)
    save_dataThree(df)


def main(start, end):
    file_name = 'data_csv.csv'

    # 抓取需要的数据，并存储成csv文件
    crawl_data(file_name, start, end)
    # 对csv数据进行筛选
    brush_data(file_name)


@app.route("/")
def index():
    type_data = pd.read_csv('品种分布数据.csv')
    type_data = type_data.rename(
        columns={'Unnamed: 0': 'name', '一级分类': 'value'})
    type_data = type_data.to_dict(orient='records')

    province_data = pd.read_csv('省份数据.csv')
    province_data = province_data.rename(
        columns={'Unnamed: 0': 'key', '产地': 'values'})

    dataAxis = province_data['key']
    daday = province_data['values']
    dataAxis = dataAxis.tolist()
    daday = daday.tolist()
    return render_template("show.html", type_data=type_data, dataAxis=dataAxis, data=daday)


if __name__ == '__main__':
    start = time.time()
    startTime = input('请输入开始时间xxxx/xx/xx:\n')
    EndTime = input('请输入结束时间xxxx/xx/xx:\n')
    main(startTime, EndTime)
    print('Spider Finished共耗时:{}秒'.format(round(time.time()-start), 2))
    print('已启动Flask服务器, 请点击下方本机5000端口查看粮食菜品分析的数据')
    app.run()
