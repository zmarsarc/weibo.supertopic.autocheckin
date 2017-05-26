# -*- coding: utf-8 -*-

import requests
import base64
import time
import re
import json
import rsa
import binascii
import pymongo
import pymongo.errors
import sys


class Session(object):

    _db_host = "db.zmarsarc.cn"
    _db_port = 27017
    _db_username = 'zmarsarc'
    _db_password = 'zeng_1213_yu'

    def __init__(self):
        self._session = None
        self._db = None
        self._config = None

    def login(self):
        s = requests.session()
        s.headers['User-Agent'] = r'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        su = self._config['auth']['user']
        prelogin_params = {
            'su': su,
            '_': int(time.time())
        }

        cont = s.get(
            self._config['prelogin']['entry'],
            params=self._config['prelogin']['params'].update(prelogin_params)).content

        cont = re.search(r"(?P<args>\{.*\})", cont)
        info = json.loads(cont.group('args'))

        rsaPubkey = int(info['pubkey'], 16)
        key = rsa.PublicKey(rsaPubkey, 65537)
        msg = str(info['servertime']) + '\t' + str(info['nonce']) + '\n' + str(self._config['auth']['pwd'])
        sp = rsa.encrypt(msg, key)
        sp = binascii.b2a_hex(sp)

        login_params = {
            "pagerefer": info['smsurl'],
            "su": su,
            "servertime": info['servertime'],
            "nonce": info['nonce'],
            "rsakv": info['rsakv'],
            "sp": sp,
        }
        respons = s.post(
            self._config['login']['entry'],
            data=self._config['login']['params'].update(login_params))

        redirect = re.findall(r'http://passport\.weibo\.com.*retcode=0', respons.content)
        s.get(redirect[0])
        self._session = s

    def _connect_db(self):
        url = "mongodb://{0}:{1}@{2}".format(
            self._db_username,
            self._db_password,
            self._db_host
        )
        try:
            client = pymongo.MongoClient(url, port=27017, connect=True)
            self._db = client.get_database('weibo')
            config = self._db.weibo.config.find()
            self._config = config.next()
        except pymongo.errors.ServerSelectionTimeoutError:
            print "Connect host :{0}:{1} failed. Server not available".format(self._db_host, self._db_port)
            sys.exit(-1)

    def __del__(self):
        if self._db is not None:
            self._db.locse()


class AccessError(RuntimeError):
    pass

