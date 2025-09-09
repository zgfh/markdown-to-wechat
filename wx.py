#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from urllib.parse import urljoin
import requests
import os
import time
import yaml
import json
import string

import os

################################################################################

def _get_token(
        app_id=os.getenv('WECHAT_APP_ID',''),  # 微信公众号AppID
        app_secret=os.getenv('WECHAT_APP_SECRET','')  # 微信公众号AppSecret
):
    """
    获取token
    :return:
    """
    url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}'
    res = requests.get(url=url)
    result = res.json()
    if result.get('access_token'):
        token = result['access_token']
        print(f"获取token成功：{token[:14]}****")
        return token
    else:
        print(f"获取token失败--{result}")

def get_token():
    """
    获取缓存token
    :return:
    """
    token = get_cache_token()
    if token:
        return token
    token = _get_token()
    if token:
        write_token(token)
    return token

def get_cache_token():
    """
    获取缓存token
    :return:
    """
    app_token_path = 'data/app_token.yaml'
    try:
        # 读取时间和token
        if not os.path.exists(app_token_path):
            return ""
        cfg_token = yaml_read(app_token_path)
        # token时间在7200s之内，返回token
        if 0 < time.time() - cfg_token['time'] < 7200-200:
            print(f"token时效内")
            return cfg_token['token']
    except TypeError:
        return ""

def write_token(token):
    """
    写入token
    :param token:
    :return:
    """
    app_token_path =  'data/app_token.yaml'
    data = {'time': time.time(), 'token': token}
    yaml_write(data, app_token_path)


def yaml_read(file):
    """
    yaml文件读取
    :param file:
    :return:
    """
    with open(file=file, mode="r", encoding="utf-8") as f:
        data = yaml.safe_load(f.read())
    return data


def yaml_write(data, file):
    """
    yaml文件写入
    :param data:
    :param file:
    :return:
    """
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, 'w', encoding='utf-8') as f:
        yaml.dump(
            data,
            stream=f,
            allow_unicode=True,  # 避免unicode编码问题
            sort_keys=False  # 不自动排序
        )


def get_material_list(count=20, offset=0, material_type='image'):
    """
    获取永久素材列表
    :param count: 返回素材的数量，取值在1到20之间
    :param offset: 0表示从第一个素材返回
    :param material_type: 素材的类型，图片（image）、视频（video）、语音 （voice）、图文（news
    :return:
    """
    url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={get_token()}"
    page_data = []  # 用于存储所有数据
    while True:
        data = {"type": material_type, "offset": offset, "count": count}  # 构造分页参数
        res = requests.post(url=url, json=data)
        if res.status_code != 200 or res.json().get('errcode'):  # 请求失败时中断
            print(f'获取永久素材列表失败--{res.text}')
            break
        result = json.loads(res.content)  # 使用result=res.json()，响应结果中文乱码
        total_count = result.get('total_count')
        page_data.extend(result['item'])
        if total_count is not None and offset >= total_count:  # 没有更多页时中断
            break
        offset += count
    print(f'获取素材列表成功')
    print(page_data)
    return page_data

def _upload_image_to_wechat(image_path):
    """
    上传图片到微信服务器，返回微信图片链接
    """
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={get_token()}"
    with open(image_path, 'rb') as fp:
        files = {'media': fp}
        res = requests.post(url, files=files).json()
        if res.get('url'):
            print(f'上传图片到微信服务器成功--{res["url"]}')
            return res['url']
        else:
            print(f'上传图片到微信服务器失败--{res}')
            return None


def upload_image_to_wechat(image_path):
    """
    上传图片到微信服务器，返回微信图片链接(永久素材)
    https://developers.weixin.qq.com/doc/subscription/api/material/permanent/api_addmaterial.html#HTTPS-%E8%B0%83%E7%94%A8
    """
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?type=image&access_token={get_token()}"
    with open(image_path, 'rb') as fp:
        files = {'media': fp}
        res = requests.post(url, files=files).json()
        if res.get('url'):
            print(f'上传图片到微信服务器成功--{res["url"]}')
            return res
        else:
            print(f'上传图片到微信服务器失败--{res}')
            return {}

def get_drawing():
    '''
    获取草稿
    '''
    url = f"https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token={get_token()}"
    data = {"offset": 0, "count": 20}  # 构造分页参数
    res = requests.post(url=url, json=data)
    
    result = json.loads(res.content)  # 使用result=res.json()，响应结果中文乱码
    return result['item']

def add_blog(articles):
    '''
    新建草稿 https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_add.html
    '''
    url = f'https://api.weixin.qq.com/cgi-bin/draft/add?access_token={get_token()}'


    res = requests.post(url=url, data=json.dumps(articles, ensure_ascii=False).encode('utf-8'))

    if res.status_code == 200:
        result = json.loads(res.content)
        if result.get('media_id'):
            print(f'新建草稿成功--{result}')
            return result
        else:
            print(f'新建草稿失败--{result}')
    else:
        print(f'新建草稿失败--{res.text}')

def add_draft(title,html_content):
    '''
    新建草稿 https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_add.html
    '''
    url = f'https://api.weixin.qq.com/cgi-bin/draft/add?access_token={get_token()}'

    # content = "<img src='https://mmbiz.qpic.cn/sz_mmbiz_jpg/hY63os7Ee2Ro6WVkfj9nvfDdpONqLwr48J2eQEYXygs3cWibLvQTHAveYWNnXOOWHO3jZldO3fr7quVj6V0X5uA/0?wx_fmt=jpeg'/>"
    # 读取文件html

    data = {
        "articles": [
            {
                "title": title,
                "author":"争光Alan",
                "digest":"", # 图文消息的摘要，仅有单图文消息才有摘要，多图文此处为空。如果本字段为没有填写，则默认抓取正文前54个字。
                # <img class=\"rich_pages wxw-img\" data-imgfileid=\"201854216\" data-ratio=\"0.665\" data-s=\"300,640\" data-src=\"https://mmbiz.qpic.cn/mmbiz/iaTKicMbV2lVd69sYcMPr12UjGopCoduMdfibRB3b15jH2ZTXXibxURpvp28H7r6LNcRmrTialLpyrFWy5azpI36u6A/640\" data-w=\"400\" type=\"block\"></
                "content":html_content, # 图文消息的具体内容，支持HTML标签，必须少于2万字符，小于1M，且此处会去除JS,涉及图片url必须来源 "上传图文消息内的图片获取URL"接口获取。外部图片url将被过滤。 图片消息则仅支持纯文本和部分特殊功能标签如商品，商品个数不可超过50个
                "content_source_url":"", # 图文消息的原文地址，即点击“阅读原文”后的URL
                "thumb_media_id":"BXwghrMb7rVBZ6pVUNCQni9eEpmo4gD1__vSSiQoGyZNhN__Ntym6AuAY61o58Dp",# 图文消息的封面图片素材id（必须是永久mediaID）
                "need_open_comment":1, # 是否打开评论，0不打开，1打开
                "only_fans_can_comment":0 # 是否粉丝才可评论，0所有人可评论，1粉丝才可评论
            }
        ]
    }

    return add_blog(data)


def free_publish(media_id):
    '''
    发布草稿
    '''
    url = f'https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={get_token()}'

    data = {
        "media_id": media_id
    }

    res = requests.post(url=url, json=data)
    res = json.loads(str(res.content, 'utf8'))
    print(res)


if __name__ == '__main__':
    x=get_drawing()
    # 格式化json输出,指定utf8编码，防止中文乱码
    print(json.dumps(x, indent=4, ensure_ascii=False))
    #add_draft("test1","test1 <br  /><br  /><br  /> <img src='https://mmbiz.qpic.cn/mmbiz/iaTKicMbV2lVd69sYcMPr12UjGopCoduMdfibRB3b15jH2ZTXXibxURpvp28H7r6LNcRmrTialLpyrFWy5azpI36u6A/640'/>")
    #add_draft(title,html_content)
    #get_material_list()

