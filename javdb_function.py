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
    # 新建 xml 文档对象
    doc = minidom.Document()

    # 创建根节点
    root = doc.createElement("root")
    # 设置根节点属性
    root.setAttribute("javdb", info_dict["url"])
    # 添加根节点到文档对象
    doc.appendChild(root)

    # 创建第一个叶子节点
    video_code = doc.createElement("video_code")
    video_code.appendChild(doc.createTextNode(info_dict["av_code"]))
    root.appendChild(video_code)

    title = doc.createElement("title")
    title.appendChild(doc.createTextNode(info_dict["title"]))
    root.appendChild(title)

    release = doc.createElement("release")
    release.appendChild(doc.createTextNode(info_dict["date"]))
    root.appendChild(release)

    d_date = doc.createElement("d_date")
    d_date.appendChild(doc.createTextNode(time.strftime("%Y-%m-%d")))
    root.appendChild(d_date)

    name = doc.createElement("name")
    name.appendChild(doc.createTextNode(info_dict["actor"]))
    root.appendChild(name)

    # 保存 xml 文档对象
    with open(nfo_path, "wb") as f:
        f.write(doc.toprettyxml(encoding="utf-8"))


def download_image_with_cookies(img_url, save_path, cookies):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Referer": "https://www.javbus.com/",  # 关键：让服务器以为你是从网页点进来的
    }
    try:
        # 下载图片
        response = requests.get(img_url, cookies=cookies, headers=headers, stream=True)
        response.raise_for_status()

        # 保存
        Path(save_path).write_bytes(response.content)
        print(f"✅ 图片已保存到: {save_path}")

    except Exception as e:
        print(f"❌ 下载图片失败: {e}")


def move_files(file_list: list[Path], target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)  # 确保目标文件夹存在

    for file_path in file_list:
        try:
            target_path = target_dir / file_path.name
            shutil.move(str(file_path), str(target_path))
            print(f"✅ 移动成功: {file_path.name} → {target_path}")
        except Exception as e:
            print(f"❌ 移动失败: {file_path.name}，原因: {e}")


def put_in_folder(info_dict, file_paths, cookies):
    print(info_dict)
    print(file_paths)
    target_folder = f'【{info_dict["actor"]}】{info_dict["av_code"]}'
    target_path = file_paths[0].parent / target_folder
    target_path.mkdir(parents=True, exist_ok=True)
    cover_name = target_folder + ".jpg"
    cover_path = target_path / cover_name

    nfo_name = target_folder + ".xml"
    nfo_path = target_path / nfo_name
    create_xml_minidom(info_dict, nfo_path)
    download_image_with_cookies(info_dict["cover_url"], cover_path, cookies)
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

            return href
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
    selenium_cookies = driver.get_cookies()
    cookies = {c["name"]: c["value"] for c in selenium_cookies}

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
    title_code = safe_get_text("h2 > strong:nth-child(1)")
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
    }, cookies


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
    selenium_cookies = driver.get_cookies()
    cookies = {c["name"]: c["value"] for c in selenium_cookies}

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
    return {
        "title": title,
        "av_code": av_code,
        "date": date,
        "actor": actors,
        "cover_url": cover_url,
        "url": url,
    }, cookies
