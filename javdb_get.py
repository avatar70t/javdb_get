#!/usr/bin/env python3
"""
批量抓取 czbooks 正文 —— 连接现有 Chrome (9222)
URL 列表文件：/Users/jianwang/Dropbox/Code/html_get/get_from_javlibrary/new.txt
"""
# 启动 Chrome 示例：
# /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/selenium-chrome-profile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from javdb_function import get_filepath_function
from javdb_function import get_video_code
from javdb_function import get_url_javdb
from javdb_function import get_url_javbus
from javdb_function import get_info_javdb
from javdb_function import get_info_javbus
from javdb_function import put_in_folder
from collections import defaultdict
import pathlib
import time
import random
import subprocess

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


def jav(driver, av_dict, cookies, site):
    # 把不同站点的函数映射好
    url_funcs = {"javdb": get_url_javdb, "javbus": get_url_javbus}
    info_funcs = {"javdb": get_info_javdb, "javbus": get_info_javbus}

    for idx, (video_code, folder_name) in enumerate(av_dict.items(), start=1):
        if site not in url_funcs:
            raise ValueError(f"未知站点: {site}")

        # 获取 URL
        url = url_funcs[site](driver, video_code)

        if not url:
            print(f"[{idx}/{len(av_dict)}] {video_code} 未找到URL，跳过")
            continue

        # 获取信息
        info_dict = info_funcs[site](driver, url)
        print(f"[{idx}/{len(av_dict)}]{video_code}")
        for key, value in info_dict.items():
            print(f"\033[36m{key}\033[0m: {value}")

        # 保存
        put_in_folder(info_dict, folder_name, cookies,driver)
        print("-" * 10)
        time.sleep(random.uniform(5, 7))


def test():
    opts = Options()
    opts.debugger_address = DEBUGGER_ADDRESS
    driver = webdriver.Chrome(options=opts)
    url = get_url_javdb(driver, "JUX-816")
    print(url)


if __name__ == "__main__":
    chrome_cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--remote-debugging-port=9222",
        "--user-data-dir=/tmp/selenium-chrome-profile",
    ]

    subprocess.Popen(chrome_cmd)

    print("等待用户登录...")
    input("登录完成后按回车继续...")

    opts = Options()
    opts.debugger_address = DEBUGGER_ADDRESS
    driver = webdriver.Chrome(options=opts)
    selenium_cookies = driver.get_cookies()
    cookies = {c["name"]: c["value"] for c in selenium_cookies}
    filelist = get_filepath_function()
    av_dict = filelist_to_dict(filelist)
    jav(driver, av_dict, cookies, "javbus")
    # jav(driver, av_dict, cookies, "javdb")
