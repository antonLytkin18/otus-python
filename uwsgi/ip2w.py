def application(environ, start_response):
    response_body = "<h1 style='color:blue'>Hello There!</h1>".encode('utf-8')
    start_response('200 OK', [
        ('Content-Type', 'text/html'),
    ])
    return response_body
