# coding: utf-8
import requests
from bs4 import BeautifulSoup

url = "https://wds.modian.com/show_weidashang_pro/6565"
header = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}

page = requests.get(url, headers=header).content
soup = BeautifulSoup(page, "html.parser", from_encoding='utf-8')

comments = soup.find('ul', id='show_comment_list').find_all('li')
for i in comments:
    print i.find('span', class_='nick').string, i.find('span', class_='nick_sup').string
