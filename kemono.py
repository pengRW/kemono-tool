import math
import time
import traceback
from urllib.parse import urlparse, parse_qs, unquote
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed

from const import *
from helper import *

from http_client import HttpClient

is_first = True

class Kemono:
    http = HttpClient()
    temp_dir = os.path.dirname(os.path.abspath(__file__))
    # 无需下载的文件名称
    skip_keywords = ["步骤图", "源文件"]
    # 可以下载的文件类型 psd会自动转换成一张png
    ok_suffix = ['.zip', '.mp4', '.psd']
    directory = os.getcwd()
    # 是否保留压缩包内目录结构
    is_retain_format = False
    # 主页无需下载的作品
    home_skip_keywords = []
    # 是否跳过作品中的第一张图片
    is_skip_first = False

    def __init__(self):
        # 创建临时目录
        os.makedirs(self.temp_dir, exist_ok=True)

    def request(self, url: str, method: str = 'GET', **kwargs):
        try:
            response = self.http.request(url, method, **kwargs)
            return response
        except Exception as e:
            if traceback.format_exc().find('Too Many Requests') != -1:
                logger.info('kemono服务器累了, 休息100s')
                time.sleep(100)

            raise e

    def download_attachments(self, attr, title: str = ''):
        download_name = unquote(attr.find('a').get('download'), 'utf-8')
        if keywords_has(self.skip_keywords, download_name):
            logger.info(f'{download_name} 已跳过')
            return

        href = attr.find('a').get('href')
        info = os.path.splitext(download_name)
        name = info[0].strip()
        suffix = info[-1].lower()
        if not keywords_has(self.ok_suffix, suffix):
            logger.info(f'{download_name} 已跳过')
            return

        if contains_chinese_or_japanese(name):
            fname = name
        else:
            fname = title

        if suffix_is_extract(suffix):
            try:
                directory = os.getcwd()
                temp_download_path = os.path.join(directory, download_name)
                extract_path = os.path.join(directory, name)
                self.http.download(href, temp_download_path)
                os.makedirs(extract_path)
                extract_compressed_file(temp_download_path, extract_path)
                logger.info(f'文件{download_name}解压成功')
                os.remove(temp_download_path)
                logger.info(f'{temp_download_path} 已删除')
                move_folder(extract_path, self.directory, False, fname)
                shutil.rmtree(extract_path)
                logger.info(f'临时目录 {extract_path} 已删除')
            except Exception as e:
                logger.error(e)
        else:
            temp_download_path = os.path.join(self.directory, f'{fname}{suffix}')
            self.http.download(href, temp_download_path)

    def download_files(self, images: list, title: str):
        if not images:
            raise Exception('def download_files() images empty！')

        threads = []
        num = 1
        for img in images:
            if num == 1 and self.is_skip_first:
                num += 1
                continue

            u = img.find('a').get('href')
            suffix = os.path.splitext(img.find('a').get('download'))[-1]
            name = f'{title}p{num}{suffix}'
            save_path = os.path.join(self.directory, name)
            thread = threading.Thread(target=self.http.download,
                                      args=(u, save_path))
            threads.append(thread)
            thread.start()
            num += 1

        for thread in threads:
            thread.join()

    @retry(stop=stop_after_attempt(STOP_MAX_ATTEMPT_NUMBER), wait=wait_fixed(WAIT_FIXED))
    def get_post(self, url: str):
        try:
            thread_semaphore.acquire()
            response = self.request(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            if not soup:
                raise Exception("抓取失败！")

            logger.info('内容获取成功')
            # 获取标题
            title = soup.find(class_='post__title').find('span').get_text(strip=True)
            logger.info(f'当前标题 {title}')
            # TODO 设置过滤条件
            # ...
            title = remove_emojis(filter_file_name(title))
            attachments = soup.find_all(class_='post__attachment')
            # 有文件下载文件 没有就下载图片
            if attachments:
                logger.info('检测到Downloads 开始下载...')
                for attr in attachments:
                    self.download_attachments(attr, title)
            else:
                logger.info('未检测到Downloads 开始下载Files...')
                images = soup.find_all(class_='post__thumbnail')
                if not images:
                    logger.info(f'{url} 没有内容跳过')
                    return

                self.download_files(images, title)
            logger.info(f' 下载完成！')
        except Exception as err:
            raise err
        finally:
            thread_semaphore.release()

    def get_author_home(self, url: str, page: int = 1, work_name=''):
        """
        从作者主页下载
        :param page: 获取多少页 0 所有
        :param url: 支持 https://kemono.su/fantia/user/* | https://kemono.su/fanbox/user/* 只要网页格式一致都行
        :param work_name: 从哪个作品开始 仅限第一页
        :return:
        """
        response = self.request(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        author = soup.find(class_='user-header__profile').find_all('span')[1].get_text(strip=True)
        logger.info(f'当前作者：{author}')
        small = soup.find('small')
        if not small:
            total_page = 1
        else:
            pagination = small.get_text(strip=True)
            total_page = math.ceil(int(re.findall(r'\d+', pagination)[-1]) / 50)

        if page < 0:
            raise Exception('def get_author_home() page 无效！')

        cursor = page
        if page > total_page or page == 0:
            cursor = total_page
            page = 0

        def posts(s):
            cards = s.find_all(class_='post-card post-card--preview')
            car_name = ''
            global is_first
            if work_name and is_first:
                index = -1
                for i, item in enumerate(cards):
                    if work_name in item.find(class_='post-card__header').get_text(strip=True):
                        index = i
                        break

                if index != -1:
                    cards = cards[index:]

                is_first = False

            for car in cards:
                try:
                    car_name = car.find(class_='post-card__header').get_text(strip=True)
                    if keywords_has(self.home_skip_keywords, car_name) or not car.find(class_='post-card__image-container'):
                        logger.info(f'[{car_name}] 已跳过')
                        continue

                    self.get_post('https://kemono.su' + car.find('a').get('href'))
                except Exception:
                    logger.error(f'{car_name} 出现错误{traceback.print_exc()}, 已跳过')
                    continue

        if cursor == 1:
            posts(soup)
            logger.info(f'{url} 下载完成！')
        else:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            current_page = 1
            domain = url.split('?')[0]
            if 'o' in query_params and page != 0:
                current_num = int(query_params['o'][0])
                current_page = math.ceil(current_num / 50) + 1

            for _ in range(cursor):
                current_num = (current_page - 1) * 50
                resp = self.request(f'{domain}?o={current_num}')
                soup = BeautifulSoup(resp.text, 'html.parser')
                posts(soup)
                current_page += 1
                logger.info(f'{domain}?o={current_num} 下载完成！')


if __name__ == '__main__':
    kemono = Kemono()
    kemono.get_author_home('https://kemono.su/fanbox/user/2408551?o=100', 1, '全体公開）簡単に作れる ミニ4駆GIF絵の素材解説')
