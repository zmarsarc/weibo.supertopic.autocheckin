import requests
import json
import time
import threading
import base64
import re
import rsa
import binascii
from bs4 import BeautifulSoup


base_url = 'http://weibo.com'
start_page = base_url + '/p/1005055657540901/myfollow'
params_interested = {'relate': 'interested', 'pids': 'plc_main', 'ajaxpagelet': '1', 'ajaxpagelet_v6': '1', '__ref': '/p/1005055657540901/myfollow?relate=interested#place', '_t': 'FM_148723148521247'}
buffer = []

def get_interest_list(url, s):
    html = s.get(url, params=params_interested).content
    scripts = find_all_scripts(html)

    interest_list = []
    target_script = find_script_by_characteristic(scripts, r'<ul class=\"member_ul clearfix\">')
    params = json.loads(target_script.string.strip('parent.FM.view(').rstrip(')'), encoding='utf-8')

    lis = find_all_lis(params)

    for li in lis:
        link = li.find('a')['href']
        interest_list.append(link.replace(r'?from=pcpage', r'/super_index'))


    return interest_list


def find_all_scripts(html):
    soup = BeautifulSoup(html, 'html.parser')
    return soup.find_all("script")


def find_all_lis(params):
    list_html = BeautifulSoup(params['html'], 'html5lib')
    ul = list_html.find('ul', class_='member_ul clearfix')
    return ul.find_all('li', class_='member_li S_bg1')


def find_script_by_characteristic(params, characteristic):
    ret = None
    for script in params:
        if -1 != script.string.find(characteristic):
            ret = script
            break
    return ret


def redirect_to_queue(queue):
    def send_msg_to_queue(func):
        def _func(url):
            ret = func(url)
            queue.append(ret)
        return _func
    return send_msg_to_queue


@redirect_to_queue(buffer)
def sign_in(url, s):
    html = s.get(url).content
    scripts = find_all_scripts(html)

    target_script = find_script_by_characteristic(scripts, r'<div class=\"PCD_header_b\">')

    action_data = json.loads(target_script.string.strip('FM.view(').rstrip(')'))
    soup = BeautifulSoup(action_data['html'], 'html5lib')
    button = soup.find('a', class_='W_btn_b btn_32px')
    title = soup.find('h1').string

    target_url = base_url + '/p/aj/general/button'

    params = create_signin_params(button['action-data'])

    result = s.get(target_url, params=params)
    return (title, result.status_code, result.content)


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


def get_msg_form_queue(queue):
    def _func(func):
        def __func():
            while True:
                if len(queue) != 0:
                    func(queue[0])
                    del queue[0]
        return __func
    return _func


@get_msg_form_queue(buffer)
def show_result(result):
    print(result[0])
    print('status code: {0}'.format(result[1]))
    msg = json.loads(result[2])
    if msg['code'] == '100000':
        print(msg['data']['alert_title'])
    elif msg['code'] == '382004':
        print(msg['msg'])
    else:
        print('undefined status code - {0} - with message: {1}'.format(msg['code'], msg['msg']))


def login():
    s = requests.session()

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
    redirect = re.search(r'http://passport.weibo.com.*retcode=0', respons.content).group()
    print redirect
    print s.get(redirect).content
    return s


if __name__ == '__main__':
    s = login()
    super_indexs = get_interest_list(start_page, s)
    threading.Thread(target=show_result).start()
    for page in super_indexs:
        threading.Thread(target=sign_in, args=(base_url + page, s)).start()
