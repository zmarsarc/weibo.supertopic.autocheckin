import requests
import json
import time
import threading
from bs4 import BeautifulSoup


base_url = 'http://weibo.com'
start_page = base_url + '/p/1005055657540901/myfollow'
params_interested = {'relate': 'interested', 'pids': 'plc_main', 'ajaxpagelet': '1', 'ajaxpagelet_v6': '1', '__ref': '/p/1005055657540901/myfollow?relate=interested#place', '_t': 'FM_148723148521247'}
buffer = []
cookie = {'SINAGLOBAL': '6842487228056.298.1487229235680', 'wvr': '6', 'wb_g_upvideo_5657540901': '1', 'YF-Page-G0': '2d32d406b6cb1e7730e4e69afbffc88c', 'SCF': 'Au5PqXBAn2VqHUzj0wjYcaNuvuCJZDbZuezr4gy9lH8mGc53tyaD76fkr6tGrUFc_7RBDLdQLO9bCJVT2lolMpA.', 'SUB': '_2A251qTZQDeRxGeNI7lUU9C7Fyz2IHXVW3yCYrDV8PUNbmtANLXnYkW9tPwx8Mg6G37h0zmEkvFKd--o_Vw..', 'SUBP': '0033WrSXqPxfM725Ws9jqgMF55529P9D9WFYQEJlxfRhbVEBQso6Vy3S5JpX5KMhUgL.Fo-cSKMfSh54eh22dJLoIE-LxKqLBo2LB.BLxKqLBo5LBoBLxK-LB.eLBo.LxKML12qLBKWk', 'SUHB': '0wnFnV1P42PN0Q', 'ALF': '1519286655', 'SSOLoginState': '1487750656', 'YF-Ugrow-G0': 'ad83bc19c1269e709f753b172bddb094', 'YF-V5-G0': 'a906819fa00f96cf7912e89aa1628751', '_s_tentry': 'login.sina.com.cn', 'UOR': ',,login.sina.com.cn', 'Apache': '5554578599321.436.1487750662789', 'ULV': '1487750662829:7:7:3:5554578599321.436.1487750662789:1487588130181'}

def get_interest_list(url):
    html = requests.get(url, params=params_interested, cookies=cookie).content
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
def sign_in(url):
    html = requests.get(url, cookies=cookie).content
    scripts = find_all_scripts(html)

    target_script = find_script_by_characteristic(scripts, r'<div class=\"PCD_header_b\">')

    action_data = json.loads(target_script.string.strip('FM.view(').rstrip(')'))
    soup = BeautifulSoup(action_data['html'], 'html5lib')
    button = soup.find('a', class_='W_btn_b btn_32px')
    title = soup.find('h1').string

    target_url = base_url + '/p/aj/general/button'

    params = create_signin_params(button['action-data'])

    result = requests.get(target_url, params=params, cookies=cookie)
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


if __name__ == '__main__':
    super_indexs = get_interest_list(start_page)
    threading.Thread(target=show_result).start()
    for page in super_indexs:
        threading.Thread(target=sign_in, args=(base_url + page,)).start()
