def capture_request(request):
    url = request['params']['request']['url']
    if 'mooc2-ans/work/mark-list' in url:  # 筛选目标 URL
        print('捕获链接:', url)