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

import os
import threading
import contextlib
import zipfile
import log
import urllib2
import sublime

try:
    import cStringIO
    StringIO = cStringIO
except ImportError:
    import StringIO


__g_mathjax_thread_started = False


def on_demand_download_mathjax():
    def background_worker(target_folder, mark_file):
        global __g_mathjax_thread_started
        __g_mathjax_thread_started = True
        archive_url = 'https://github.com/downloads/timonwong/OmniMarkupPreviewer/mathjax.zip'
        try:
            urllib2.install_opener(urllib2.build_opener(urllib2.ProxyHandler()))
            log.info('Downloading MathJax from "%s"', archive_url)

            with contextlib.closing(urllib2.urlopen(archive_url)) as archive_file:
                archive_stream = StringIO.StringIO(archive_file.read())
                archive_stream.seek(0)
                log.info('Extrating contents from mathjax.zip ...')
                with contextlib.closing(zipfile.ZipFile(archive_stream)) as zip_file:
                    # Check archive first
                    for path in zip_file.namelist():
                        if path[0] == '/' or path.find('../') != -1 or path.find('..\\') != -1:
                            # Not a safe zip file
                            log.error('"%s" contains invalid files', archive_url)
                            return
                    # Install
                    if not os.path.exists(target_folder):
                        os.makedirs(target_folder)
                    for path in zip_file.namelist():
                        if path.endswith('/'):
                            # Create directory
                            folder = os.path.join(target_folder, path)
                            if not os.path.exists(folder):
                                os.makedirs(folder)
                        else:
                            # Write file
                            with open(os.path.join(target_folder, path), 'wb') as f:
                                f.write(zip_file.read(path))
                    # Complete
                    with open(mark_file, 'w') as f:
                        f.write('')
                    log.info('MathJax succesfully extracted into "%s"', target_folder)
        except:
            log.exception("Error on downloading MathJax")
            message = (
                'MathJax download failed, you have to download and extract it manually.\n'
                'After extracting, you have to create a file named "%s".\n'
                'Download Url:\n "%s"\n'
                'Target folder: "%s"' % (
                    os.path.join(user_folder, '.MATHJAX.DOWNLOADED'), archive_url, target_folder
                )
            )
            sublime.set_timeout(lambda: sublime.message_dialog(message), 0)
        finally:
            global __g_mathjax_thread_started
            __g_mathjax_thread_started = False

    global __g_mathjax_thread_started
    if __g_mathjax_thread_started:
        # In progress
        return

    user_folder = os.path.join(sublime.packages_path(), 'User', 'OmniMarkupPreviewer')
    target_folder = os.path.join(user_folder, 'public')
    mathjax_folder = os.path.join(target_folder, 'mathjax')
    mark_file = os.path.join(user_folder, '.MATHJAX.DOWNLOADED')
    if os.path.exists(mark_file) and os.path.exists(mathjax_folder):
        # Already downloaded
        return

    thread = threading.Thread(
        name='Thread-on_demand_download_mathjax', target=background_worker,
        args=[target_folder, mark_file]
    )
    thread.start()
