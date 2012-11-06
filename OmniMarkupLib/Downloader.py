import os
import re
import urllib2
import subprocess
import tempfile
import log


class BinaryNotFoundError(Exception):
    pass


class NonCleanExitError(Exception):
    def __init__(self, returncode):
        self.returncode = returncode

    def __str__(self):
        return repr(self.returncode)


class CliDownloader(object):
    def __init__(self, settings):
        self.settings = settings

    def find_binary(self, name):
        for dir in os.environ['PATH'].split(os.pathsep):
            path = os.path.join(dir, name)
            if os.path.exists(path):
                return path

        raise BinaryNotFoundError('The binary %s could not be located' % name)

    def execute(self, args):
        proc = subprocess.Popen(args, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        output = proc.stdout.read()
        self.stderr = proc.stderr.read()
        returncode = proc.wait()
        if returncode != 0:
            error = NonCleanExitError(returncode)
            error.output = self.stderr
            raise error
        return output


class WgetDownloader(CliDownloader):
    def __init__(self, settings):
        self.settings = settings
        self.wget = self.find_binary('wget')

    def clean_tmp_file(self):
        os.remove(self.tmp_file)

    def download(self, url, error_message, timeout, tries):
        if not self.wget:
            return False

        self.tmp_file = tempfile.NamedTemporaryFile().name
        command = [self.wget, '--connect-timeout=' + str(int(timeout)),
            '-o', self.tmp_file, '-O', '-', '-U', 'OmniMarkup Downloader']

        command.append(url)

        if self.settings.get('http_proxy'):
            os.putenv('http_proxy', self.settings.get('http_proxy'))
            if not self.settings.get('https_proxy'):
                os.putenv('https_proxy', self.settings.get('http_proxy'))
        if self.settings.get('https_proxy'):
            os.putenv('https_proxy', self.settings.get('https_proxy'))

        while tries > 0:
            tries -= 1
            try:
                result = self.execute(command)
                self.clean_tmp_file()
                return result
            except (NonCleanExitError) as (e):
                error_line = ''
                with open(self.tmp_file) as f:
                    for line in list(f):
                        if re.search('ERROR[: ]|failed: ', line):
                            error_line = line
                            break

                if e.returncode == 8:
                    regex = re.compile('^.*ERROR (\d+):.*', re.S)
                    if re.sub(regex, '\\1', error_line) == '503':
                        # GitHub and BitBucket seem to rate limit via 503
                        log.info('Downloading %s was rate limited, trying again', url)
                        continue
                    error_string = 'HTTP error ' + re.sub('^.*? ERROR ', '',
                        error_line)

                elif e.returncode == 4:
                    error_string = re.sub('^.*?failed: ', '', error_line)
                    # GitHub and BitBucket seem to time out a lot
                    if error_string.find('timed out') != -1:
                        log.info('Downloading %s timed out, trying again', url)
                        continue

                else:
                    error_string = re.sub('^.*?(ERROR[: ]|failed: )', '\\1',
                        error_line)

                error_string = re.sub('\\.?\s*\n\s*$', '', error_string)
                log.info('%s %s downloading %s.', error_message, error_string, url)
            self.clean_tmp_file()
            break
        return False


class CurlDownloader(CliDownloader):
    def __init__(self, settings):
        self.settings = settings
        self.curl = self.find_binary('curl')

    def download(self, url, error_message, timeout, tries):
        if not self.curl:
            return False
        command = [self.curl, '-f', '--user-agent', 'OmniMarkup Downloader',
            '--connect-timeout', str(int(timeout)), '-sS']

        command.append(url)

        if self.settings.get('http_proxy'):
            os.putenv('http_proxy', self.settings.get('http_proxy'))
            if not self.settings.get('https_proxy'):
                os.putenv('HTTPS_PROXY', self.settings.get('http_proxy'))
        if self.settings.get('https_proxy'):
            os.putenv('HTTPS_PROXY', self.settings.get('https_proxy'))

        while tries > 0:
            tries -= 1
            try:
                return self.execute(command)
            except (NonCleanExitError) as (e):
                if e.returncode == 22:
                    code = re.sub('^.*?(\d+)\s*$', '\\1', e.output)
                    if code == '503':
                        # GitHub and BitBucket seem to rate limit via 503
                        log.info('Downloading %s was rate limited, trying again', url)
                        continue
                    error_string = 'HTTP error ' + code
                elif e.returncode == 6:
                    error_string = 'URL error host not found'
                elif e.returncode == 28:
                    # GitHub and BitBucket seem to time out a lot
                    log.info('Downloading %s timed out, trying again', url)
                    continue
                else:
                    error_string = e.output.rstrip()

                log.info('%s %s downloading %s.', error_message, error_string, url)
            break
        return False


class UrlLib2Downloader(object):
    def __init__(self, settings):
        self.settings = settings

    def download(self, url, error_message, timeout, tries):
        http_proxy = self.settings.get('http_proxy')
        https_proxy = self.settings.get('https_proxy')
        if http_proxy or https_proxy:
            proxies = {}
            if http_proxy:
                proxies['http'] = http_proxy
                if not https_proxy:
                    proxies['https'] = http_proxy
            if https_proxy:
                proxies['https'] = https_proxy
            proxy_handler = urllib2.ProxyHandler(proxies)
        else:
            proxy_handler = urllib2.ProxyHandler()
        handlers = [proxy_handler]

        # secure_url_match = re.match('^https://([^/]+)', url)
        # if secure_url_match != None:
        #   secure_domain = secure_url_match.group(1)
        #   bundle_path = self.check_certs(secure_domain, timeout)
        #   if not bundle_path:
        #       return False
        #   handlers.append(VerifiedHTTPSHandler(ca_certs=bundle_path))
        urllib2.install_opener(urllib2.build_opener(*handlers))

        while tries > 0:
            tries -= 1
            try:
                request = urllib2.Request(url,
                    headers={"User-Agent": "OmniMarkup Downloader"}
                )
                http_file = urllib2.urlopen(request, timeout=timeout)
                return http_file.read()

            except (urllib2.HTTPError) as (e):
                # Bitbucket and Github ratelimit using 503 a decent amount
                if str(e.code) == '503':
                    log.info('Downloading %s was rate limited, trying again', url)
                    continue
                log.info('%s HTTP error %s downloading %s.', error_message, str(e.code), url)

            except (urllib2.URLError) as (e):
                # Bitbucket and Github timeout a decent amount
                if str(e.reason) == 'The read operation timed out' or \
                        str(e.reason) == 'timed out':
                    log.info('Downloading %s timed out, trying again', url)
                    continue
                log.info('%s URL error %s downloading %s.', error_message, str(e.reason), url)
            break
        return False
