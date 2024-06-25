import hashlib
import os
import re
import shutil
import zipfile

import emoji
import ftfy
import patoolib
from PIL import Image

from logger import logger


def parse_url(url):
    # parse urls
    downloadable = re.search(r'^https://(kemono\.su|coomer\.su)/([^/]+)/user/([^/]+)($|/post/([^/]+)$)', url)
    if not downloadable:
        return None

    return downloadable.group(1)


# get file hash
def get_file_hash(file: str):
    sha256_hash = hashlib.sha256()
    with open(file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest().lower()


def suffix_is_extract(suffix):
    """
    :param suffix: demo:.zip .gz...
    :return:
    """
    return bool(suffix in ['.zip', '.rar', '.7z', '.gz', '.tar'])


def suffix_is_video(suffix):
    """
    :param suffix: demo:.zip .gz...
    :return:
    """
    return bool(
        suffix in ['.mp4', '.wmv', '.asf', '.asx', '.rm', '.rmvb', '.mov', '.m4v', '.avi', '.dat', '.mkv', '.flv',
                   '.vob'])


def is_image(file_path):
    # 检测文件类型
    try:
        with Image.open(file_path) as img:
            img.verify()
            return True
    except (IOError, SyntaxError):
        return False


def contains_chinese_or_japanese(text: str):
    """
    识别字符串中是否包含中文或者日文
    :param text:
    :return: bool
    """
    pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]')
    return bool(pattern.search(text))


def filter_file_name(input_string):
    return re.sub('[/:*?"<>|]', '-', input_string)


def file_move(file_path: str, dst_dir: str, name: str):
    """
    把文件从 file_path 移动到 dst_dir 文件名重复会重命名 old.zip => diff-old.zip
    :param file_path: demo：C:\\Users\\xxx\\Desktop\\test.zip
    :param dst_dir: demo: D:\\zips
    :param name: 文件名称 用于判断是否存在
    :return: 保存的位置
    """
    if os.path.exists(os.path.join(dst_dir, name)):
        name = f'diff-{name}'

    new_path = os.path.join(dst_dir, name)
    shutil.move(file_path, new_path)
    return new_path


def move_folder(src_folder, dest_folder, retain_format=False, rename=None):
    """
    移动文件夹并可配置保留目录格式和重命名文件

    Args:
    src_folder (str): 源文件夹路径
    dest_folder (str): 目标文件夹路径
    retain_format (bool, optional): 是否保留原文件夹下的目录格式，默认为 False
    rename (str, optional): 重命名文件的基础名称

    Returns:
    None
    """
    rename_template = "{}_p{}"
    for root, dirs, files in os.walk(src_folder):
        for file in files:
            src_path = os.path.join(root, file)
            if is_image(src_path) or suffix_is_video(os.path.splitext(file)[1]) or file.lower().endswith('.psd'):
                if rename:
                    dest_file = rename_template.format(rename, files.index(file)) + os.path.splitext(file)[1]
                else:
                    base_dir = os.path.basename(os.path.normpath(root))
                    if ftfy.badness.is_bad(base_dir) and rename:
                        base_dir = rename

                    dest_file = rename_template.format(base_dir, files.index(file)) + os.path.splitext(file)[1]

                if retain_format:
                    dest_path = os.path.join(dest_folder, os.path.relpath(root, src_folder), dest_file)
                else:
                    dest_path = os.path.join(dest_folder, dest_file)

                if file.lower().endswith('.psd'):
                    logger.info(f'检测到psd文件已转换成png')
                    with Image.open(src_path) as img:
                        img.save(os.path.splitext(dest_path)[0] + '.png', 'PNG')
                    continue

                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.move(src_path, dest_path)


def is_encrypted(zip_path):
    """
    检测压缩包是否加密
    :param zip_path:
    :return:
    """
    zf = zipfile.ZipFile(zip_path)
    for zip_file in zf.infolist():
        return bool(zip_file.flag_bits & 0x1)


def extract_compressed_file(file_path, extract_dir='.', password=None):
    """
    解压 file_path 到 extract_dir
    :param file_path: 压缩包的位置
    :param extract_dir: 解压到的目录 默认当前运行目录
    :param password: 密码
    :return:
    """
    # file_extension = os.path.splitext(file_path)[1].lower()
    # os.makedirs(extract_dir, exist_ok=True)
    # if file_extension != ".zip":
    #     raise Exception(f"脚本暂时不支持[{file_extension}]这个格式")

    if is_encrypted(file_path):
        logger.info('检测到当前压缩包已加密')
        if not password:
            password = input("请输入密码: ")

    patoolib.extract_archive(file_path, outdir=extract_dir, password=password)


def keywords_has(keywords: list, name: str):
    return any(re.search(keyword, name, re.IGNORECASE) for keyword in keywords)


def remove_emojis(text):
    # 使用 emoji 库将文本中的表情符号替换为空字符串
    text = emoji.replace_emoji(text, replace=' ')
    return text


if __name__ == '__main__':
    move_folder('/Users/mac/Desktop/kemono/src/tests', '/Users/mac/Desktop/kemono/src', True)
    # u = 'https://kemono.su/fanbox/user/3316400'
    # extract_compressed_file('/Users/mac/Desktop/kemono/src/fanbox animation.zip',
    #                         '/Users/mac/Desktop/kemono/tests/fanbox animation')
    # extract_compressed_file('C:\\Users\\ximae\\Desktop\\xx.zip', 'C:\\Users\\ximae\\Desktop\\tmp')
    # print(parse_url(u))
    # res = request_(u, 'get', **{'stream': True})
    # print(res.text)
