import os
import sys
import time
import traceback

from .kemono import Kemono
from .logger import logger
from .const import menu_dict


def main():
    print("""注意本脚本只支持从https://kemono.su 网站抓取，其他网站无效。
      _____________________________________________
      mail: q1925186789@gmail.com
      Github: https://github.com/pengRW
      _____________________________________________
      [1] 抓取单个作品
      [2] 从作者主页抓取整页作品
      [3] Exit
    ___________________________________________________""")
    while True:
        t = input('在键盘中输入菜单选项 [1,2,3]: ')
        if t in ['1', '2', '3']:
            break

    if t == '3':
        print('感谢使用！')
        time.sleep(1)
        sys.exit()

    if sys.platform == 'win32':
        os.system('cls')
    else:
        os.system('clear')

    print(f'当前模式：{menu_dict[t]}')
    kemono = Kemono()
    while True:
        directory = input('请设置保存的位置（只能是目录 默认当前运行位置）：')
        if os.path.isdir(directory):
            kemono.directory = directory
            break

    print(f'当前脚本保存的位置是： {directory}')
    s = input('是否跳过作品中的第一张图片（n or y）默认n:')
    kemono.is_skip_first = s == 'y'

    is_proxy = input('是否配置本地代理 （n or y）默认n:')
    if is_proxy == 'y':
        kemono.http.use_proxy = True
        port = input('请输入本地代理端口（默认v2rayN的10809）：')
        if port:
            kemono.http.proxy_url = f'http://localhost:{port}'

    while 1:
        url = input('请输入要抓取的URL：')
        if not url:
            continue

        print(f'当前URL:{url}')
        try:
            if t == '1':
                kemono.get_post(url)
            else:
                skip_str = input('要跳过的关键字（多个使用,分割）：')
                if skip_str:
                    logger.debug(f'已设置跳过名称中包含[{skip_str}]的作品')
                    kemono.home_skip_keywords = skip_str.split(',')
                else:
                    logger.debug('开始下载所有作品')

                while 1:
                    page = input('抓取几页（默认1页 0 表示所有）：')
                    if not page:
                        page = 1
                        break

                    if page.isdigit():
                        break

                logger.debug(f'当前抓取{page}页')
                kemono.get_author_home(url, int(page))
        except:
            traceback.print_exc()

