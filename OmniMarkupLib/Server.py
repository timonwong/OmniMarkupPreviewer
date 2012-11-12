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
import sys
import os
import os.path
import base64
import sublime
from OmniMarkupLib import log
from OmniMarkupLib import LibraryPathManager
from OmniMarkupLib.Setting import Setting
from OmniMarkupLib.RendererManager import RendererManager
from OmniMarkupLib.Common import RenderedMarkupCache, Future


__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)


DEFAULT_STATIC_FILES_DIR = os.path.normpath(os.path.join(__path__, '..', 'public'))
USER_STATIC_FILES_DIR = os.path.normpath(os.path.join(sublime.packages_path(),
                                         'User', 'OmniMarkupPreviewer', 'public'))
DEFAULT_TEMPLATE_FILES_DIR = os.path.normpath(os.path.join(__path__, '..', 'templates'))
USER_TEMPLATE_FILES_DIR = os.path.normpath(os.path.join(sublime.packages_path(),
                                           'User', 'OmniMarkupPreviewer', 'templates'))


def _mk_folders(folders):
    for folder in folders:
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except:
                pass

_mk_folders([USER_STATIC_FILES_DIR, USER_TEMPLATE_FILES_DIR])

LibraryPathManager.push_search_path(os.path.dirname(sys.executable))
LibraryPathManager.push_search_path(os.path.join(__path__, 'libs'))
try:
    from cherrypy import wsgiserver
    import bottle
    from bottle import Bottle, ServerAdapter
    from bottle import static_file, request, template
finally:
    LibraryPathManager.pop_search_path()
    LibraryPathManager.pop_search_path()

bottle.TEMPLATE_PATH = [USER_TEMPLATE_FILES_DIR, DEFAULT_TEMPLATE_FILES_DIR]


# Create a new app stack
app = Bottle()


@app.route('/public/<filepath:path>')
def handler_public(filepath):
    """ Serving static files """
    global DEFAULT_STATIC_FILES_DIR
    # User static files have a higher priority
    if os.path.exists(os.path.join(USER_STATIC_FILES_DIR, filepath)):
        return static_file(filepath, root=USER_STATIC_FILES_DIR)
    return static_file(filepath, root=DEFAULT_STATIC_FILES_DIR)


@app.route('/local/<base64_encoded_path>')
def handler_local(base64_encoded_path):
    """ Serving local files """
    fullpath = base64.urlsafe_b64decode(base64_encoded_path)
    basename = os.path.basename(fullpath)
    dirname = os.path.dirname(fullpath)
    return static_file(basename, root=dirname)


@app.post('/api/query')
def handler_api_query():
    """ Querying for updates """
    entry = None
    try:
        obj = request.json
        buffer_id = obj['buffer_id']
        timestamp = str(obj['timestamp'])

        storage = RenderedMarkupCache.instance()
        entry = storage.get_entry(buffer_id)
    except:
        pass

    if entry is None:
        return {
            'timestamp': -1,
            'filename': '',
            'dirname': '',
            'html_part': None
        }

    if entry.timestamp == timestamp:  # Keep old entry
        return {
            'timestamp': entry.timestamp,
            'filename': None,
            'dirname': None,
            'html_part': None
        }
    else:
        return {
            'timestamp': entry.timestamp,
            'filename': entry.filename,
            'dirname': entry.dirname,
            'html_part': entry.html_part
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
    # A browser refresh always get the latest result
    f = Future(render_text_by_buffer_id, buffer_id)
    sublime.set_timeout(f, 0)
    entry = f.result()
    entry = entry or RenderedMarkupCache.instance().get_entry(buffer_id)
    if entry is None:
        return bottle.HTTPError(
            404,
            'buffer_id(%d) is not valid (not open or unsupported file format)' % buffer_id
        )
    setting = Setting.instance()
    return template(setting.html_template_name,
                    buffer_id=buffer_id,
                    ajax_polling_interval=setting.ajax_polling_interval,
                    mathjax_enabled=setting.mathjax_enabled,
                    **entry)


class StoppableCherryPyServer(ServerAdapter):
    """ HACK for making a stoppable server """
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

    def __init__(self, host='127.0.0.1', port='51004'):
        self.server = StoppableCherryPyServer(host=host, port=port)
        self.runner = Server.ServerThread(self.server)
        self.runner.daemon = True
        self.runner.start()

    def stop(self):
        log.info('Bottle server shuting down...')
        self.server.shutdown()
        self.runner.join()
