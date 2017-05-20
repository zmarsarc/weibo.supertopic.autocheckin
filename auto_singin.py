# -*- coding: utf-8 -*-
# 被自己的代码丑哭了
import requests
import json
import time
import base64
import re
import rsa
import binascii
import threading
import Queue
from bs4 import BeautifulSoup


base_url = 'http://weibo.com'
start_page = base_url + '/p/1005055657540901/myfollow'
params_interested = {'relate': 'interested', 'pids': 'plc_main', 'ajaxpagelet': '1', 'ajaxpagelet_v6': '1', '__ref': '/p/1005055657540901/myfollow?relate=interested#place', '_t': 'FM_148723148521247'}


def get_interest_list(url, s):
    html = s.get(url, params=params_interested).content
    scripts = find_all_script_tags(html)

    interest_list = []
    target_script = find_script_by_characteristic(scripts, r'<ul class=\"member_ul clearfix\">')
    params = json.loads(target_script.string.strip('parent.FM.view(').rstrip(')'), encoding='utf-8')

    lis = find_all_li_tags(params['html'])

    for li in lis:
        link = li.find('a')['href']
        interest_list.append(link.replace(r'?from=pcpage', r'/super_index'))

    return interest_list


def find_all_script_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    return soup.find_all("script")


def find_all_li_tags(html):
    list_html = BeautifulSoup(html, 'html.parser')
    ul = list_html.find('ul', class_='member_ul clearfix')
    return ul.find_all('li', class_='member_li S_bg1')


def find_script_by_characteristic(params, characteristic):
    ret = None
    for script in params:
        if -1 != script.string.find(characteristic):
            ret = script
            break
    return ret


class SignInTask(object):

    def __init__(self, title, url, params):
        self.title = title
        self.url = url
        self.params = params


class SignInResult(object):

    def __init__(self, title, raw):
        self.title = title
        self.raw = raw


def sign_in(task, s):
    result = s.get(task.url, params=task.params)
    return SignInResult(task.title, result)


def setup_sign_in_task(url, s):
    html = s.get(url).content
    scripts = find_all_script_tags(html)
    target_script = find_script_by_characteristic(scripts, r'<div class=\"PCD_header_b\">')
    action_data = json.loads(target_script.string.strip('FM.view(').rstrip(')'))
    soup = BeautifulSoup(action_data['html'], 'html.parser')
    button = soup.find('a', class_='W_btn_b btn_32px')
    title = soup.find('h1').string
    target_url = base_url + '/p/aj/general/button'
    params = create_signin_params(button['action-data'])
    return SignInTask(title, target_url, params)


def create_signin_params(action_data):
    action_data_lines = action_data.replace('&', '\n').splitlines()
    action_data_pairs = {}
    for line in action_data_lines:
        pair = line.replace('=', '\n').splitlines()
        action_data_pairs[pair[0]] = pair[1]
    params = {'ajwvr': '6',
              'location': 'page_100808_super_index',
              '__rnd': str(int(time.time()))}
    params.update(action_data_pairs)
    return params


def login():
    s = requests.session()
    s.headers['User-Agent'] = r'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'

    url = 'https://login.sina.com.cn/sso/prelogin.php'
    params = {
        'entry': 'weibo',
        'callback': 'sinaSSOController.preloginCallBack',
        'su': base64.b64encode('18502330411'),
        'rsakt': 'mod',
        'checkpin': '1',
        'client': 'ssologin.js(v1.4.18)',
        '_': int(time.time())
    }

    cont = s.get(url, params=params).content
    cont = re.search(r"(?P<args>\{.*\})", cont)
    info = json.loads(cont.group('args'))

    rsaPubkey = int(info['pubkey'], 16)
    key = rsa.PublicKey(rsaPubkey, 65537)
    msg = str(info['servertime']) + '\t' + str(info['nonce']) + '\n' + str('zeng-1213-yu')
    sp = rsa.encrypt(msg, key)
    sp = binascii.b2a_hex(sp)

    params = {
        "entry": "weibo",
        "gateway": "1",
        "from": "",
        "savestate": "7",
        "useticket": "1",
        "pagerefer": info['smsurl'],
        "vsnf": "1",
        "su": base64.b64encode('18502330411'),
        "service": "miniblog",
        "servertime": info['servertime'],
        "nonce": info['nonce'],
        "pwencode": "rsa2",
        "rsakv": info['rsakv'],
        "sp": sp,
        "sr": "1280*720",
        "encoding": "UTF-8",
        "prelt": '49',
        "url": "http://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack",
        "returntype": "META"
    }

    respons = s.post("http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.18)", data=params)
    redirect = re.findall(r'http://passport\.weibo\.com.*retcode=0', respons.content)
    s.get(redirect[0])
    return s


if __name__ == '__main__':

    import math
    # status_code: 382004 今天已经签到过了
    #              100000 签到成功

    msg = Queue.Queue()
    s = login()
    super_indexs = get_interest_list(start_page, s)
    tasks = [setup_sign_in_task(base_url + p, s) for p in super_indexs]

    second_in_hour = 60 * 60
    second_in_day = 24 * second_in_hour
    timezone_offset = -8
    next_day = math.ceil(time.time() / second_in_day) * second_in_day
    wait_seconds = (next_day - time.time()) + (timezone_offset * second_in_hour)
    print("standby, task will run in {0} seconds".format(wait_seconds))
    # time.sleep(wait_seconds + 60)  # 0001时签到

    for task in tasks:
        thread = threading.Thread(target=lambda: msg.put(sign_in(task, s))).start()
        time.sleep(0.5)

    while True:
        if not msg.empty():
            ret = msg.get()
            content = ret.raw.json()
            try:
                print ret.title, content['msg'], content['data']['alert_title']
            except KeyError:
                pass
            except TypeError as e:
                with open('error_log.txt', 'w') as f:
                    encoder = json.JSONEncoder()
                    f.write(encoder.encode(content))
                print e.message
                exit(-1)

