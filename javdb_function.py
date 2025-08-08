from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from html import unescape
from xml.dom import minidom
import argparse
import re
import time
import configparser
from pathlib import Path
import requests
import shutil

# 加载配置文件
config = configparser.ConfigParser()
config_file = Path(__file__).parent / "config.ini"
config.read(config_file, encoding="utf-8")


def get_filepath_function():
    parser = argparse.ArgumentParser()
    parser.add_argument("total_temp_file")
    filelist_temp = parser.parse_args().total_temp_file

    with open(filelist_temp, "r", encoding="utf_8") as file:
        file_paths = [Path(line.rstrip()) for line in file]
    return file_paths


def get_video_code(filepath):  # 文件名取番号
    file_name_code_get = filepath.name.lower()
    file_name_code_get = file_name_code_get.replace(" ", "")
    if "hhd800.com@" in file_name_code_get:
        file_name_code_get = file_name_code_get.replace("hhd800.com@", "")
    if "_bit" in file_name_code_get:
        file_name_code_get = file_name_code_get.replace("_bit", "")

    matchObj = re.search(r"[a-zA-Z]{1,9}-?\d{2,7}", file_name_code_get, re.M | re.I)
    code = matchObj.group(0)
    matchENG = re.search("[a-zA-Z]*", code, re.M | re.I).group(0)
    matchNum = re.search(r"\d{2,7}", code, re.M | re.I).group(0)
    if len(matchNum) == 5:
        if matchNum.startswith("00"):
            matchNum = matchNum[2:]
        if matchNum.startswith("0"):
            matchNum = matchNum[1:]
    code = matchENG + "-" + matchNum.zfill(3)
    if code.startswith("t-"):
        code = code.replace("-", "")

    return code.upper()


def female_actor_only(actors):
    female_actors = []
    actors_list = actors.split(" ")
    if actors == "N/A":
        return "有码演员"
    for actor in actors_list:
        if actor.endswith("♀"):
            female_actors.append(actor.replace("♀", ""))
    return " ".join(female_actors)


def create_xml_minidom(info_dict, nfo_path):
    try:
        # 新建 xml 文档对象
        doc = minidom.Document()

        # 创建根节点
        root = doc.createElement("root")
        root.setAttribute("javdb", info_dict.get("url", ""))  # 用 get 避免 KeyError
        doc.appendChild(root)

        # 子节点封装函数，减少重复
        def add_node(name, text):
            elem = doc.createElement(name)
            elem.appendChild(doc.createTextNode(text))
            root.appendChild(elem)

        add_node("video_code", info_dict.get("av_code", ""))
        add_node("title", info_dict.get("title", ""))
        add_node("release", info_dict.get("date", ""))
        add_node("d_date", time.strftime("%Y-%m-%d"))
        add_node("name", info_dict.get("actor", ""))

        # 保存
        with open(nfo_path, "wb") as f:
            f.write(doc.toprettyxml(encoding="utf-8"))

        print(f"✅ {nfo_path.name}")

    except Exception as e:
        print(f"❌ 生成 XML 失败: {nfo_path.name} - {e}")


def download_image_with_cookies(img_url, save_path, cookies,driver):
    
    headers = {
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Referer": driver.current_url
        }
    print(headers)
    input()

    try:
        # 下载图片
        response = requests.get(img_url, cookies=cookies, headers=headers, stream=True)
        response.raise_for_status()

        # 保存
        Path(save_path).write_bytes(response.content)
        print(f"✅ {save_path.name}")

    except Exception as e:
        print(f"❌ 下载图片失败: {e}")


def move_files(file_list: list[Path], target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)  # 确保目标文件夹存在

    for file_path in file_list:
        try:
            target_path = target_dir / file_path.name
            shutil.move(str(file_path), str(target_path))
            print(f"✅ {target_path.name}")
        except Exception as e:
            print(f"❌ {file_path.name}，原因: {e}")


def check_cn(target_folder, file_name_check):
    # 初始化标志变量
    cn_mark = 0
    unc_mark = 0

    # 获取文件名的主干部分并转为大写
    stem_upper = file_name_check.stem.upper()

    # 定义可能的标记关键词
    cn_suffixes = {"C", "CH"}  # 文件名末尾的 CN 标志
    cn_keywords = {"-C", "-C_", "-UC"}  # 文件名中包含的 CN 关键词
    unc_keywords = {"-U", "UNCENSORED"}  # 未剪辑标志

    # 检查是否是 CN 标志
    if any(stem_upper.endswith(suffix) for suffix in cn_suffixes):
        cn_mark = 1
    if any(keyword in stem_upper for keyword in cn_keywords):
        cn_mark = 1

    # 检查是否是未剪辑标志
    if any(keyword in stem_upper for keyword in unc_keywords):
        unc_mark = 1
    if cn_mark or unc_mark:
        target_folder = target_folder + "-"
        if unc_mark:
            target_folder = target_folder + "U"
        if cn_mark:
            target_folder = target_folder + "C"

    return target_folder


def put_in_folder(info_dict, file_paths, cookies,driver):
    target_folder = f'【{info_dict["actor"]}】{info_dict["av_code"]}'
    target_folder = check_cn(target_folder, file_paths[0])

    target_path = file_paths[0].parent / target_folder
    target_path.mkdir(parents=True, exist_ok=True)
    cover_name = target_folder + ".jpg"
    cover_path = target_path / cover_name

    nfo_name = target_folder + ".xml"
    nfo_path = target_path / nfo_name
    create_xml_minidom(info_dict, nfo_path)
    download_image_with_cookies(info_dict["cover_url"], cover_path, cookies,driver)
    move_files(file_paths, target_path)


# ----------javdb----------


def get_url_javdb(driver, video_code):
    time.sleep(2)
    try:
        url = f"https://javdb458.com/search?q={video_code}"
        driver.get(url)
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".movie-list"))
        )
        # 查找第一个链接
        first_link = driver.find_element(By.CSS_SELECTOR, ".movie-list a")
        av_code = first_link.find_element(By.TAG_NAME, "strong").text
        if av_code == video_code:
            href = first_link.get_attribute("href")

            return href + "?locale=zh"
    except Exception as e:
        print(f"❌ 获取电影链接失败: {url}")
        print(f"错误类型: {type(e).__name__}, 信息: {e}")
        return ""  # 或 return None，视你程序需求


def get_info_javdb(driver, url):
    driver.get(url)

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "strong.current-title"))
        )
    except:
        return {
            "title": "",
            "title_code": "",
            "av_code": "",
            "date": "",
            "actor": "",
            "video_cover": "",
        }

    def safe_get_text(selector):
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
        except:
            return ""

    def safe_get_attr(selector, attr):
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).get_attribute(attr)
        except:
            return ""

    def get_item_after(label, items):
        try:
            index = items.index(label)
            return items[index + 1].strip()
        except (ValueError, IndexError):
            return ""

    title = safe_get_text("strong.current-title")
    cover_url = safe_get_attr("div.column-video-cover img", "src")

    container = safe_get_text(".panel.movie-panel-info")
    items = [item.strip() for item in container.split("\n")]

    av_code = get_item_after("番號:", items)
    date = get_item_after("日期:", items)
    actors = get_item_after("演員:", items)

    return {
        "title": title,
        "av_code": av_code,
        "date": date,
        "actor": female_actor_only(actors),
        "cover_url": cover_url,
        "url": url,
    }


# ----------javbus----------


def get_url_javbus(driver, video_code):
    try:
        url = f"https://www.javbus.com/search/{video_code}&type=&parent=ce"
        driver.get(url)
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#waterfall"))
        )
    except Exception as e:
        print(f"❌ 获取电影链接失败: {url}")
        print(f"错误类型: {type(e).__name__}, 信息: {e}")
        return ""  # 类型统一为 str

    try:
        first_link = driver.find_element(
            By.CSS_SELECTOR, "#waterfall .item.masonry-brick"
        )
        if video_code.lower() in first_link.text.lower():  # 忽略大小写匹配更稳
            movie_url = first_link.find_element(
                By.CSS_SELECTOR, ".movie-box"
            ).get_attribute("href")
            return movie_url
        else:
            print("⚠️ 搜索结果中未找到匹配的 video_code")
            return ""
    except Exception as e:
        print(f"❌ 页面结构异常或未找到结果：{e}")
        return ""


def get_info_javbus(driver, url):
    driver.get(url)

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "body > div.container > h3")
            )
        )
    except:
        return {
            "title": "",
            "av_code": "",
            "date": "",
            "actor": "",
            "video_cover": "",
        }

    def safe_get_text(selector):
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
        except:
            return ""

    def safe_get_attr(selector, attr):
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).get_attribute(attr)
        except:
            return ""

    def get_item_after(label, items):
        try:
            index = items.index(label)
            return items[index + 1].strip()
        except (ValueError, IndexError):
            return ""

    cover_url = safe_get_attr(
        "body > div.container > div.row.movie > div.col-md-9.screencap > a > img", "src"
    )
    title = safe_get_text("body > div.container > h3")

    container = safe_get_text(
        "body > div.container > div.row.movie > div.col-md-3.info"
    )

    items = [item.strip() for item in container.split("\n")]

    for item in items:
        if item.startswith("發行日期:"):
            date = item.split(":")[-1].strip()
        if item.startswith("識別碼"):
            av_code = item.split(":")[-1].strip()
    actors = get_item_after("演員:", items)
    if actors == "暫無出演者資訊":
        actors = "有码演员"

    return {
        "title": title,
        "av_code": av_code,
        "date": date,
        "actor": actors,
        "cover_url": cover_url,
        "url": url,
    }
