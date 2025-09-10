#!/usr/bin/env python
##public/upload_news.py
# -*- coding: utf-8 -*-
"""
推送文章到微信公众号
"""
from calendar import c
from datetime import datetime
from datetime import timedelta
from weakref import ref
from pyquery import PyQuery
from datetime import date, timedelta
import time
import html
import urllib
import markdown
from markdown.extensions import codehilite
import os
import hashlib
import pickle
from pathlib import Path
import wx as publish_client
import requests
import json
import urllib.request
import random
import string

CACHE = {}

CACHE_STORE = "data/cache.bin"

def dump_cache():
    fp = open(CACHE_STORE, "wb")
    pickle.dump(CACHE, fp)

def init_cache():
    global CACHE
    if os.path.exists(CACHE_STORE):
        fp = open(CACHE_STORE, "rb")
        CACHE = pickle.load(fp)
        #print(CACHE)
        return
    dump_cache()

def cache_get(key):
    if key in CACHE:
        return CACHE[key]
    return None


def file_digest(file_path):
    """
    计算文件的md5值
    """
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        md5.update(f.read())
    return md5.hexdigest()

def cache_update(file_path):
    digest = file_digest(file_path)
    CACHE[digest] = "{}:{}".format(file_path, datetime.now())
    dump_cache()

def file_processed(file_path):
    digest = file_digest(file_path)
    return cache_get(digest) != None

def upload_image_from_path(image_path):
  image_digest = file_digest(image_path)
  res = cache_get(image_digest)
  if res != None:
      return res[0], res[1]

  print("uploading image {}".format(image_path))
  try:
    media_json = publish_client.upload_image_to_wechat(image_path) ##永久素材
    media_id = media_json['media_id']
    media_url = media_json['url']
    CACHE[image_digest] = [media_id, media_url]
    dump_cache()
    print("file: {} => media_id: {}".format(image_path, media_id))
    return media_id, media_url
  except Exception as e:
    print("upload image error: {}".format(e))
    return None, None

def upload_image(img_url):
  """
  * 上传临时素材
  * 1、临时素材media_id是可复用的。
  * 2、媒体文件在微信后台保存时间为3天，即3天后media_id失效。
  * 3、上传临时素材的格式、大小限制与公众平台官网一致。
  """
  resource = urllib.request.urlopen(img_url)
  name = img_url.split("/")[-1]
  f_name = "data/{}".format(name)
  if "." not in f_name:
    f_name = f_name + ".png"
  with open(f_name, 'wb') as f:
    f.write(resource.read())
  return upload_image_from_path(f_name)

def get_images_from_markdown(content):
    lines = content.split('\n')
    images = []
    for line in lines:
        line = line.strip()
        if line.startswith('![') and line.endswith(')'):
            image = line.split('(')[1].split(')')[0].strip()
            images.append(image)
    return images

def fetch_attr(content, key):
    """
    从markdown文件中提取属性
    """
    lines = content.split('\n')
    for line in lines:
        if line.startswith(key):
            return line.split(':')[1].strip()
    return ""

def render_markdown(content):
    exts = ['markdown.extensions.extra',
            'markdown.extensions.tables',
            'markdown.extensions.toc',
            'markdown.extensions.sane_lists',
            codehilite.makeExtension(
                guess_lang=False,
                noclasses=True,
                pygments_style='monokai'
            ),]
    post =  "".join(content.split("---\n")[2:])
    html = markdown.markdown(post, extensions=exts)
    open("data/origi.html", "w").write(html)
    return css_beautify(html)

def update_images_urls(content, uploaded_images):
    for image, meta in uploaded_images.items():
        orig = "({})".format(image)
        new = "({})".format(meta[1])
        #print("{} -> {}".format(orig, new))
        content = content.replace(orig, new)
    return content

def replace_para(content):
    res = []
    for line in content.split("\n"):
        if line.startswith("<p>"):
            line = line.replace("<p>", gen_css("para"))
            line = line.replace("<ol>", gen_css("ol"))
            line = line.replace("<li>", gen_css("li"))
        res.append(line)
    return "\n".join(res)

def gen_css(path, *args):
    tmpl = open("./assets/{}.tmpl".format(path), "r").read()
    return tmpl.format(*args)

def replace_header(content):
    res = []
    for line in content.split("\n"):
        l = line.strip()
        if l.startswith("<h") and l.endswith(">") > 0:
            tag = l.split(' ')[0].replace('<', '')
            value = l.split('>')[1].split('<')[0]
            digit = tag[1]
            font =  (18 + (4 - int(tag[1])) * 2) if (digit >= '0' and digit <= '9') else 18
            res.append(gen_css("sub", tag, font, value, tag))
        else:
            res.append(line)
    return "\n".join(res)

def replace_links(content):
    pq = PyQuery(open('data/origi.html').read())
    links = pq('a')
    refs = []
    index = 1
    if len(links) == 0:
        return content
    for l in links.items():
        link = gen_css("link", l.text(), index)
        index += 1
        refs.append([l.attr('href'), l.text(), link])

    for r in refs:
        orig = "<a href=\"{}\">{}</a>".format(html.escape(r[0]), r[1])
        print(orig)
        content = content.replace(orig, r[2])
    content = content + "\n" + gen_css("ref_header")
    content = content + """<section class="footnotes">"""
    index = 1
    for r in refs:
        l = r[2]
        line = gen_css("ref_link", index, r[1], r[0])
        index += 1
        content += line + "\n"
    content = content + "</section>"
    return content

def fix_image(content):
    pq = PyQuery(open('data/origi.html').read())
    imgs = pq('img')
    for line in imgs.items():
        alt_name=line.attr('alt')
        if alt_name.startswith("alt"):
            alt_name = ""
        origin_link="""<img alt="{}" src="{}" />""".format(line.attr('alt'), line.attr('src'))
        link = """<img alt="{}" src="{}" />""".format(alt_name, line.attr('src'))
        figure = gen_css("figure", link, alt_name)
        content = content.replace(origin_link, figure)
    return content

def format_fix(content):
    content = content.replace("<ol>\n", "<ol>")
    content = content.replace("</li>\n", "</li>")
    content = content.replace("background: #272822", gen_css("code"))
    content = content.replace("""<pre style="line-height: 125%">""", """<pre style="line-height: 125%; color: white; font-size: 11px;">""")
    return content

def css_beautify(content):
    content = format_fix(content)
    content = replace_para(content)
    content = replace_header(content)
    content = replace_links(content)
    content = fix_image(content)
    content = gen_css("header") + content + "</section>"
    return content


def upload_media_news(post_path):
    """
    上传到微信公众号素材
    """
    content = open (post_path , 'r').read()
    TITLE = fetch_attr(content, 'title').strip('"').strip('\'')
    gen_cover = fetch_attr(content, 'gen_cover').strip('"')
    images = get_images_from_markdown(content)
    print(TITLE)
    if len(images) == 0 or gen_cover == "true" :
        letters = string.ascii_lowercase
        seed = ''.join(random.choice(letters) for i in range(10))
        print(seed)
        images = ["https://picsum.photos/seed/" + seed + "/400/600"] + images
    uploaded_images = {}
    for image in images:
        media_id = ''
        media_url = ''
        if image.startswith("http"):
            media_id, media_url = upload_image(image)
        else:
            image_path = os.path.join(os.path.dirname(post_path), image)
            media_id, media_url = upload_image_from_path(image_path)
        if media_id != None:
            uploaded_images[image] = [media_id, media_url]

    content = update_images_urls(content, uploaded_images)

    THUMB_MEDIA_ID = (len(images) > 0 and uploaded_images[images[0]][0]) or ''
    AUTHOR = '争光'
    RESULT = render_markdown(content)
    # 截取/docs/后面的路径,包含/docs/
    link =  "/docs/"+post_path.split('/docs/', 1)[-1].replace('.md', '')
    digest = fetch_attr(content, 'subtitle').strip().strip('"').strip('\'')
    CONTENT_SOURCE_URL = 'https://www.daozzg.com/{}'.format(link)

    articles = {
        'articles':
        [
            {
                "title": TITLE,
                "thumb_media_id": THUMB_MEDIA_ID,
                "author": AUTHOR,
                "digest": digest,
                "show_cover_pic": 1,
                "content": RESULT,
                "content_source_url": CONTENT_SOURCE_URL
            }
            # 若新增的是多图文素材，则此处应有几段articles结构，最多8段
        ]
    }

    fp = open('data/result.html', 'w')
    fp.write(RESULT)
    fp.close()

    resp = publish_client.add_blog(articles)
    print(resp)
    media_id = resp['media_id']
    cache_update(post_path)
    return resp

def run(string_date,post_path):
    #string_date = "2023-03-13"
    print(string_date)
    pathlist = Path(post_path).glob('**/*.md')
    for path in pathlist:
        path_str = str(path)
        if path_str.endswith("_index.md"):
            continue
        content = open (path_str , 'r').read()
        date = fetch_attr(content, 'date').strip()
        if string_date in date:
            if file_processed(path_str) and os.environ.get("FORCE") != "true":
                print("{} has been processed".format(path_str))
                continue
            print(path_str)
            news_json = upload_media_news(path_str)
            print(news_json);
            print('successful')

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

if __name__ == '__main__':
    print("begin sync to wechat")
    init_cache()
    start_time = time.time() # 开始时间
    for x in daterange(datetime.now() - timedelta(days=2), datetime.now() + timedelta(days=2)):
        print("start time: {}".format(x.strftime("%m/%d/%Y, %H:%M:%S")))
        string_date = x.strftime('%Y-%m-%d')
        print(string_date)
        run(string_date, "../zzg-blog/content/docs/")
    end_time = time.time() #结束时间
    print("程序耗时%f秒." % (end_time - start_time))
