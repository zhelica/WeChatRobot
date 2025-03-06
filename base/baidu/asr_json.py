# coding=utf-8

import sys
import json
import base64
import time

IS_PY3 = sys.version_info.major == 3

if IS_PY3:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
    from urllib.parse import urlencode
    timer = time.perf_counter
else:
    from urllib2 import urlopen, Request
    from urllib2 import URLError
    from urllib import urlencode
    timer = time.clock

API_KEY = 'qcHiiokQMUGqczfRqQw2rSNR'
SECRET_KEY = 'eu3xUaXjrqXH5c5CcsYcDSlPARWb5UOJ'

# 极速版配置
DEV_PID = 80001
ASR_URL = 'http://vop.baidu.com/pro_api'
SCOPE = 'brain_enhanced_asr'  # 有此scope表示有极速版能力，没有请在网页里开通极速版

TOKEN_URL = 'http://aip.baidubce.com/oauth/2.0/token'


def fetch_token():
    params = {'grant_type': 'client_credentials',
              'client_id': API_KEY,
              'client_secret': SECRET_KEY}
    post_data = urlencode(params)
    if IS_PY3:
        post_data = post_data.encode('utf-8')
    req = Request(TOKEN_URL, post_data)
    try:
        f = urlopen(req)
        result_str = f.read()
    except URLError as err:
        print('token http response http code : ' + str(err.code))
        result_str = err.read()
    if IS_PY3:
        result_str = result_str.decode()

    result = json.loads(result_str)
    if 'access_token' in result.keys() and 'scope' in result.keys():
        if SCOPE and (not SCOPE in result['scope'].split(' ')):  # SCOPE = False 忽略检查
            raise DemoError('scope is not correct')
        print('SUCCESS WITH TOKEN: %s  EXPIRES IN SECONDS: %s' % (result['access_token'], result['expires_in']))
        return result['access_token']
    else:
        raise DemoError('MAYBE API_KEY or SECRET_KEY not correct: access_token or scope not found in token response')


class DemoError(Exception):
    pass


def recognize_audio(file_path):
    AUDIO_FILE = file_path
    FORMAT = AUDIO_FILE[-3:]  # 文件后缀只支持 pcm/wav/amr 格式，极速版额外支持m4a 格式
    RATE = 16000  # 固定值
    CUID = '123456PYTHON'

    token = fetch_token()

    speech_data = []
    with open(AUDIO_FILE, 'rb') as speech_file:
        speech_data = speech_file.read()

    length = len(speech_data)
    if length == 0:
        raise DemoError('file %s length read 0 bytes' % AUDIO_FILE)
    speech = base64.b64encode(speech_data)
    if IS_PY3:
        speech = str(speech, 'utf-8')

    params = {
        'dev_pid': DEV_PID,
        'format': FORMAT,
        'rate': RATE,
        'token': token,
        'cuid': CUID,
        'channel': 1,
        'speech': speech,
        'len': length
    }
    post_data = json.dumps(params, sort_keys=False)
    req = Request(ASR_URL, post_data.encode('utf-8'))
    req.add_header('Content-Type', 'application/json')

    try:
        begin = timer()
        f = urlopen(req)
        result_str = f.read()
        print("Request time cost %f" % (timer() - begin))
    except URLError as err:
        print('asr http response http code : ' + str(err.code))
        result_str = err.read()

    if IS_PY3:
        result_str = str(result_str, 'utf-8')

    result_json = json.loads(result_str)
    result_text = result_json.get('result', [''])[0]  # 获取结果中的第一个元素

    return result_text


if __name__ == '__main__':
    # 示例调用
    audio_file_path = 'E:/data/WeChat Files/audio/output.m4a'
    recognized_text = recognize_audio(audio_file_path)
    print("Recognized Text:", recognized_text)