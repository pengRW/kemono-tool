import threading

menu_dict = {
    '1': '单作品模式',
    '2': '主页作品模式'
}

# 同时最大线程数
MAX_CONCURRENT_THREADS = 5
# 并发下载数
thread_semaphore = threading.Semaphore(MAX_CONCURRENT_THREADS)
# 重试几次
STOP_MAX_ATTEMPT_NUMBER = 2
# 重试间隔时间
WAIT_FIXED = 2
