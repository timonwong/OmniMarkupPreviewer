"""
Copyright (c) 2013 Timon Wong

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

import sublime

import base64
import os
import sys
import threading

from . import log, LibraryPathManager
from .Setting import Setting
from .RendererManager import RenderedMarkupCache, RendererManager
from .Common import Future

__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)

# Add path for finding cherrypy server and bottlepy web framework
LibraryPathManager.add_search_path(os.path.dirname(sys.executable))
LibraryPathManager.add_search_path(os.path.join(__path__, 'libs'))

from cherrypy import wsgiserver
import bottle
# bottle.debug(True)
from bottle import Bottle, ServerAdapter
from bottle import static_file, request, template

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote


DEFAULT_STATIC_FILES_DIR = os.path.normpath(os.path.join(__path__, '..', 'public'))
USER_STATIC_FILES_DIR = None
DEFAULT_TEMPLATE_FILES_DIR = os.path.normpath(os.path.join(__path__, '..', 'templates'))
USER_TEMPLATE_FILES_DIR = None


def init():
    global USER_STATIC_FILES_DIR
    global USER_TEMPLATE_FILES_DIR

    USER_STATIC_FILES_DIR = os.path.normpath(os.path.join(sublime.packages_path(),
                                             'User', 'OmniMarkupPreviewer', 'public'))
    USER_TEMPLATE_FILES_DIR = os.path.normpath(os.path.join(sublime.packages_path(),
                                               'User', 'OmniMarkupPreviewer', 'templates'))

    def mk_folders(folders):
        for folder in folders:
            if not os.path.exists(folder):
                try:
                    os.makedirs(folder)
                except:
                    pass

    mk_folders([USER_STATIC_FILES_DIR, USER_TEMPLATE_FILES_DIR])
    bottle.TEMPLATE_PATH = [USER_TEMPLATE_FILES_DIR, DEFAULT_TEMPLATE_FILES_DIR]


# Create a new app stack
app = Bottle()


def get_static_public_file(filepath):
    if os.path.exists(os.path.join(USER_STATIC_FILES_DIR, filepath)):
        return static_file(filepath, root=USER_STATIC_FILES_DIR)
    return static_file(filepath, root=DEFAULT_STATIC_FILES_DIR)


@app.route('/public/<filepath:path>')
def handler_public(filepath):
    """Serving static files."""
    # User static files have a higher priority
    return get_static_public_file(filepath)


@app.route('/local/<base64_encoded_path>')
def handler_local(base64_encoded_path):
    """Serving local files."""
    fullpath = base64.urlsafe_b64decode(base64_encoded_path).decode('utf-8')
    fullpath = unquote(fullpath)
    basename = os.path.basename(fullpath)
    dirname = os.path.dirname(fullpath)
    return static_file(basename, root=dirname)


@app.post('/api/query')
def handler_api_query():
    """Querying for updates."""
    entry = None
    try:
        obj = request.json
        buffer_id = obj['buffer_id']
        timestamp = str(obj['timestamp'])
        entry = RenderedMarkupCache.instance().get_entry(buffer_id)
    except:
        return None

    if entry is None or entry.disconnected:
        return {'status': 'DISCONNECTED'}

    if entry.timestamp == timestamp:  # Keep old entry
        return {'status': 'UNCHANGED'}

    result = {
        'status': 'OK',
        'timestamp': entry.timestamp,
        'revivable_key': entry.revivable_key,
        'filename': entry.filename,
        'dirname': entry.dirname,
        'html_part': entry.html_part
    }
    return result


@app.post('/api/revive')
def handler_api_revive():
    """Revive buffer."""
    try:
        obj = request.json
        revivable_key = obj['revivable_key']
    except:
        return None

    f = Future(lambda: RendererManager.revive_buffer(revivable_key))
    sublime.set_timeout(f, 0)
    buffer_id = f.result()

    if buffer_id is None:
        return {'status': 'NOT FOUND'}

    # Check wheter buffer is ready
    if not RenderedMarkupCache.instance().exists(buffer_id):
        # Add this view to the queue
        sublime.set_timeout(lambda: RendererManager.enqueue_buffer_id(buffer_id), 0)
        return {'status': 'NOT READY'}

    return {'status': 'OK', 'buffer_id': buffer_id}


@app.route('/view/<buffer_id:int>')
def handler_view(buffer_id):
    # A browser refresh always get the latest result
    f = Future(lambda: RendererManager.enqueue_buffer_id(buffer_id, immediate=True))
    sublime.set_timeout(f, 0)
    entry = f.result()
    entry = entry or RenderedMarkupCache.instance().get_entry(buffer_id)
    if entry is None:
        error_msg = """\
'buffer_id(%d) is not valid (closed or unsupported file format)'

**NOTE:** If you run multiple instances of Sublime Text, you may want to adjust
the `server_port` option in order to get this plugin work again."""
        error_msg = error_msg % buffer_id
        raise bottle.HTTPError(404, error_msg)
    setting = Setting.instance()
    return template(setting.html_template_name,
                    buffer_id=buffer_id,
                    ajax_polling_interval=setting.ajax_polling_interval,
                    mathjax_enabled=setting.mathjax_enabled,
                    **entry)


class StoppableCherryPyServer(ServerAdapter):
    """HACK for making a stoppable server"""

    def __int__(self, *args, **kwargs):
        super(ServerAdapter, self).__init__(*args, **kwargs)
        self.srv = None

    def run(self, handler):
        self.srv = wsgiserver.CherryPyWSGIServer(
            (self.host, self.port), handler, numthreads=2, timeout=2, shutdown_timeout=2
        )
        self.srv.start()

    def shutdown(self):
        try:
            if self.srv is not None:
                self.srv.stop()
        except:
            log.exception('Error on shutting down cherrypy server')
        self.srv = None


def bottle_run(server):
    try:
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

    def __init__(self, host='127.0.0.1', port='51004'):
        self.server = StoppableCherryPyServer(host=host, port=port)
        self.runner = Server.ServerThread(self.server)
        self.runner.daemon = True
        self.runner.start()

    def stop(self):
        log.info('Bottle server shuting down...')
        self.server.shutdown()
        self.runner.join()
