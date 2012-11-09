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
import sys
import threading
import contextlib
import urllib2
import sublime
import zipfile
from OmniMarkupLib.Downloader import *

try:
    import cStringIO
    StringIO = cStringIO
except ImportError:
    import StringIO


MATHJAX_LIB_URL = 'http://cloud.github.com/downloads/timonwong/OmniMarkupPreviewer/mathjax.zip'


class MathJaxOnDemandDownloader(threading.Thread):
    def __init__(self, target_folder, mark_file):
        threading.Thread.__init__(self)
        #
        self.target_folder = target_folder
        self.mark_file = mark_file
        self.settings = {}

    def download_url(self, url, error_message):
        has_ssl = 'ssl' in sys.modules and hasattr(urllib2, 'HTTPSHandler')
        is_ssl = url.startswith('https://')

        if (is_ssl and has_ssl) or not is_ssl:
            downloader = UrlLib2Downloader(self.settings)
        else:
            for downloader_class in [CurlDownloader, WgetDownloader]:
                try:
                    downloader = downloader_class(self.settings)
                    break
                except BinaryNotFoundError:
                    pass

        if not downloader:
            self.log('Unable to download MathJax library due to invalid downloader')
            return False

        timeout = 60
        return downloader.download(url.replace(' ', '%20'), error_message, timeout, 3)

    def run(self):
        try:
            self.do_work()
        finally:
            global __g_mathjax_thread_started
            __g_mathjax_thread_started = False

    def do_work(self):
        downloading_message = 'Downloading MathJax from %s' % MATHJAX_LIB_URL
        log.info(downloading_message)
        sublime.set_timeout(lambda: sublime.status_message(downloading_message), 0)
        archive = self.download_url(MATHJAX_LIB_URL, 'Unable to download mathjax library from %s' % MATHJAX_LIB_URL)
        if not archive:
            # Download failed
            return

        with contextlib.closing(StringIO.StringIO(archive)) as archive_stream:
            archive_stream.seek(0)
            log.info('Extrating contents from mathjax.zip ...')
            with contextlib.closing(zipfile.ZipFile(archive_stream)) as zip_file:
                # Check archive first
                for path in zip_file.namelist():
                    if path[0] == '/' or path.find('../') != -1 or path.find('..\\') != -1:
                        # Not a safe zip file
                        log.error('mathjax.zip contains invalid files')
                        return
                # Install
                if not os.path.exists(self.target_folder):
                    os.makedirs(self.target_folder)
                for path in zip_file.namelist():
                    if path.endswith('/'):
                        # Create directory
                        folder = os.path.join(self.target_folder, path)
                        if not os.path.exists(folder):
                            os.makedirs(folder)
                    else:
                        # Write file
                        with open(os.path.join(self.target_folder, path), 'wb') as f:
                            f.write(zip_file.read(path))
                # Complete
                with open(self.mark_file, 'w') as f:
                    f.write('')
                success_message = 'MathJax succesfully installed into %s' % self.target_folder
                log.info(success_message)
                sublime.set_timeout(lambda: sublime.status_message(success_message), 0)


__g_mathjax_thread_started = False


def on_demand_download_mathjax():
    global __g_mathjax_thread_started
    if __g_mathjax_thread_started:
        # Already started
        return

    user_folder = os.path.join(sublime.packages_path(), 'User', 'OmniMarkupPreviewer')
    target_folder = os.path.join(user_folder, 'public')
    mathjax_folder = os.path.join(target_folder, 'mathjax')
    mark_file = os.path.join(user_folder, '.MATHJAX.DOWNLOADED')
    if os.path.exists(mark_file) and os.path.exists(mathjax_folder):
        # Already downloaded
        return

    thread = MathJaxOnDemandDownloader(target_folder, mark_file)
    __g_mathjax_thread_started = True
    thread.start()
