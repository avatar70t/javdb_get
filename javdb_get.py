#!/usr/bin/env python3
"""
批量抓取 czbooks 正文 —— 连接现有 Chrome (9222)
URL 列表文件：/Users/jianwang/Dropbox/Code/html_get/get_from_javlibrary/new.txt
"""
# 启动 Chrome 示例：
# /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/selenium-chrome-profile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from javdb_function import get_filepath_function
from javdb_function import get_video_code
from javdb_function import get_from_url
from javdb_function import get_info
from javdb_function import put_in_folder
from collections import defaultdict
import subprocess
import pathlib
import time
import random

# ========== 可调参数 ==========
DEBUGGER_ADDRESS = "localhost:9222"
WAIT_SECOND = 2  # 页面加载等待
directory = pathlib.Path(__file__).parent


def filelist_to_dict(filelist):
    av_dict = defaultdict(list)
    for av_path in filelist:
        av_folder = av_path.parent
        video_code = get_video_code(av_path)
        if video_code:
            av_dict[video_code].append(av_path)
    return av_dict


def main():
    opts = Options()
    opts.debugger_address = DEBUGGER_ADDRESS
    driver = webdriver.Chrome(options=opts)
    filelist = get_filepath_function()

    av_dict = filelist_to_dict(filelist)
    for video_code in av_dict.keys():
        url, av_code_in_search_page = get_from_url(driver, video_code)
        if av_code_in_search_page == video_code:
            url += "?locale=zh"
            info_dict = get_info(driver, url)
            put_in_folder(info_dict, av_dict[video_code])
        sleep_time = random.uniform(5, 7)
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
