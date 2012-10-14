"""
Copyright (c) 2012 Timon Wong

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import threading
import os.path
import wsgiref.simple_server
import log
import sublime
from RendererManager import RendererManager
from Common import RenderedMarkupCache, Future


__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)

STATIC_FILES_DIR = os.path.normpath(os.path.join(__path__, '..', 'public'))
TEMPLATE_FILES_DIR = os.path.normpath(os.path.join(__path__, '..', 'templates'))

import bottle
from bottle import Bottle, ServerAdapter
from bottle import static_file, request, template

bottle.TEMPLATE_PATH = [TEMPLATE_FILES_DIR]


# Create a new app stack
app = Bottle()


@app.route('/public/<filepath:path>')
def handler_public(filepath):
    """ Serving static files """
    global STATIC_FILES_DIR
    return static_file(filepath, root=STATIC_FILES_DIR)


@app.post('/api/query')
def handler_api_query():
    """ Querying for updates """
    try:
        obj = request.json
        buffer_id = obj['buffer_id']
        timestamp = str(obj['timestamp'])

        storage = RenderedMarkupCache.instance()
        entry = storage.get_entry(buffer_id)

        if entry.timestamp == timestamp:
            return {
                'timestamp': entry.timestamp,
                'filename': None,
                'dirname': None,
                'html_part': None
            }
        return {
            'timestamp': entry.timestamp,
            'filename': entry.filename,
            'dirname': entry.dirname,
            'html_part': entry.html_part
        }
    except:
        return {
            'timestamp': -1,
            'filename': '',
            'dirname': '',
            'html_part': None
        }


def render_text_by_buffer_id(buffer_id):
    valid_view = None
    for window in sublime.windows():
        if valid_view is not None:
            break
        for view in window.views():
            if view.buffer_id() == buffer_id:
                valid_view = view
                break
    if valid_view is None:
        return None
    RendererManager.queue_view(valid_view, immediate=True)
    return RenderedMarkupCache.instance().get_entry(buffer_id)


@app.route('/view/<buffer_id:int>')
def handler_view(buffer_id):
    storage = RenderedMarkupCache.instance()
    entry = storage.get_entry(buffer_id)
    if entry is None:  # Loading text into cache by buffer_id, if not exists
        f = Future(render_text_by_buffer_id, buffer_id)
        sublime.set_timeout(f, 0)
        entry = f.result()
    if entry is None:
        return bottle.HTTPError(404, 'buffer_id(%d) is not valid' % buffer_id)
    return template(
        'github', filename=entry.filename, dirname=entry.dirname,
        buffer_id=buffer_id, timestamp=entry.timestamp, text=entry.html_part
    )


class StoppableWSGIServerAdapter(ServerAdapter):
    """ HACK for making a stoppable server """
    def __int__(self, *args, **kargs):
        ServerAdapter.__init__(self, *args, **kargs)
        self.srv = None

    def __del__(self):
        if self.srv is not None:
            self.stop()

    def run(self, handler):
        class QuietHandler(wsgiref.simple_server.WSGIRequestHandler):
            def log_request(*args, **kw):
                pass
        self.srv = wsgiref.simple_server.make_server(
            self.host, self.port, handler,
            server_class=wsgiref.simple_server.WSGIServer,
            handler_class=QuietHandler
        )
        self.srv.serve_forever()

    def stop(self):
        self.srv.shutdown()
        self.srv = None


def bottle_run(server):
    try:
        global app

        log.info("Bottle v%s server starting up..." % (bottle.__version__))
        log.info("Listening on http://%s:%d/" % (server.host, server.port))
        server.run(app)
    except:
        raise


class Server(object):
    class ServerThread(threading.Thread):
        def __init__(self, server):
            threading.Thread.__init__(self)
            self.server = server

        def run(self):
            bottle_run(server=self.server)

    def __init__(self, port):
        self.server = StoppableWSGIServerAdapter(port=port)
        t = Server.ServerThread(self.server)
        t.daemon = True
        t.start()

    def stop(self):
        self.server.stop()
