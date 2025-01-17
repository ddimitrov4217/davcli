# -*- coding: UTF-8 -*-
# vim:ft=python:et:ts=4:sw=4:ai

import os
from datetime import datetime
from getpass import getpass
from base64 import b64encode
from urllib import parse
import http.client as http
from xml.etree import ElementTree as ET
from pytz import timezone
import ssl


# http://www.webdav.org/specs/rfc4918.html
class BaseClient:
    def __init__(self, davpath, target):
        self.davpath = davpath
        self.base_auth = None
        self.created_paths = set()
        self.urlp = parse.urlparse(target)
        self.base_url = parse.urljoin(self.urlp.path, davpath)
        self.print_headers = False
        self.con = None
        self.http_proxy = None

    def _get_connection(self):
        if self.con is None:
            if self.http_proxy is not None:
                conn_host, conn_port = self.http_proxy
            else:
                conn_host, conn_port = self.urlp.hostname, self.urlp.port

            if self.urlp.scheme == 'https':
                ctx = ssl.create_default_context()
                # XXX Опционално изключване на проверката
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                self.con = http.HTTPSConnection(conn_host, conn_port, context=ctx)
            else:
                self.con = http.HTTPConnection(conn_host, conn_port)

            if self.http_proxy is not None:
                self.con.set_tunnel(self.urlp.hostname, self.urlp.port)

        return self.con

    def _request(self, method, path, reader=None, **argv):
        print('  >>>', method, path)
        try:
            url = parse.urljoin(self.base_url, parse.quote(path))
            print('      URL', url)
            con = self._get_connection()
            if 'headers' not in argv:
                argv['headers'] = {}

            if self.base_auth is not None:
                argv['headers'].update(self.base_auth)
            if self.print_headers:
                self._dump_headers_int(argv['headers'])

            con.request(method, url, **argv)
            res = con.getresponse()
            print('  <<<', res.status, res.reason)
            self._dump_headers(res)

            if reader is not None:
                reader(res)
            return res.status
        finally:
            con.close()

    def _dump_headers(self, res):
        if not self.print_headers:
            return
        self._dump_headers_int(res.headers)

    def _dump_headers_int(self, headers):
        for header in headers:
            print(' '*5, header, ':', headers[header])

    def auth(self, username, password):
        if password is None:
            password = getpass('Password for %s: ' % username)
        authstr = '%s:%s' % (username, password)
        authstr = b64encode(authstr.encode('UTF-8')).decode()
        self.base_auth = {'Authorization': 'Basic %s' % authstr}

    def proxy(self, proxy_str):
        if proxy_str is not None:
            host, port = proxy_str.split(':')
            self.http_proxy = host, int(port)


class MirrorClient(BaseClient):
    def __init__(self, davpath, target):
        BaseClient.__init__(self, davpath, target)

    def mkcol(self, fnm):
        success = True
        dnames = os.path.dirname(fnm).split('/')
        for p in range(len(dnames)):
            dname = '/'.join(dnames[:p+1])
            if dname not in self.created_paths:
                status = self.propfind(dname)
                if status == 404:
                    status = self._request('MKCOL', dname)
                    success = success and status < 400
                if success:
                    self.created_paths.add(dname)
        return success

    def put(self, fnm):
        with open(fnm, 'rb') as fin:
            status = self._request('PUT', fnm, body=fin)
        return status < 400

    def delete(self, fnm):
        status = self._request('DELETE', fnm)
        return status < 400 or status == 404

    def propfind(self, dname):
        query = ('<?xml version="1.0"?>'
                 '<propfind xmlns="DAV:">'
                 '   <prop><resourcetype/></prop>'
                 '</propfind>')
        return self._request('PROPFIND', dname, body=query)


class DownloadClient(BaseClient):
    def __init__(self, davpath, target):
        BaseClient.__init__(self, davpath, target)

    def path_info(self, dname):
        result = []

        def reader(res):
            if res.status != 207:
                return
            ns = {'D': 'DAV:'}
            root = ET.parse(res)

            for elem in root.findall('.//D:response', ns):
                name = elem.find('D:href', ns).text
                name = name.replace('/%s' % self.davpath, '')
                name = parse.unquote(name)

                prop = elem.find('D:propstat/D:prop', ns)
                rt = prop.find('D:resourcetype/D:*', ns)
                rt = rt is not None

                dt = prop.find('D:getlastmodified', ns).text
                # dt = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%SZ')
                dt = datetime.strptime(dt, '%a, %d %b %Y %H:%M:%S %Z')
                dt = timezone("UTC").localize(dt).astimezone(timezone("EET"))

                cl = prop.find('D:getcontentlength', ns)
                cl = int(cl.text) if cl is not None else None
                if name != dname:
                    result.append((rt, cl, dt, name))

        query = (
            '<?xml version="1.0"?>'
            '<propfind xmlns="DAV:">'
            '  <prop>'
            '    <resourcetype/>'
            '    <getlastmodified/>'
            '    <getcontentlength/>'
            '  </prop>'
            '</propfind>')

        self._request('PROPFIND', headers={'Depth': 1}, path=dname, reader=reader, body=query)
        return result

    def download(self, dname, fout):
        reader = self._create_reader(fout)
        return self._request('GET', path=dname, reader=reader)

    def update(self, dname, dsize, fout):
        # https://www.rfc-editor.org/rfc/rfc9110#name-range-requests
        reader = self._create_reader(fout)
        headers = {'Range': 'bytes=%d-' % dsize}
        return self._request('GET', headers=headers, path=dname, reader=reader)

    def _create_reader(self, fout):
        def reader(res):
            if res.status not in (200, 206):
                return

            pbar = self.progress(int(res.getheader('content-length'), 0))

            while True:
                data = res.read(20480)
                if data is None or len(data) == 0:
                    break
                fout.write(data)
                pbar.update(len(data))
            pbar.update(0, thre=0, end='\n\n')

        return reader

    class progress:
        def __init__(self, clength):
            self.clength = clength
            self.ulength = 0
            self.progress = 0
            self.measure = list(zip((1, 2**10, 2**20), ('B', 'KB', 'MB')))

        def update(self, ldata, thre=5, end='\r'):
            self.ulength += ldata
            progress = int(100*self.ulength/self.clength)
            if progress - self.progress >= thre:
                self.progress = progress
                self.log(end=end)

        def log(self, end='\r'):
            div, mea = self.measure[0]
            for div_, mea_ in self.measure[1:]:
                if self.ulength//div_ <= 1:
                    break
                div, mea = div_, mea_
            end = '%s%s' % (' '*30, end)
            if div > 1:
                print('{0:d}% {1:,.2f} / {2:,.2f} {3}'.format(
                    self.progress, self.ulength/div, self.clength/div, mea),
                    end=end)
            else:
                print('{0:d}% {1:,d} / {2:,d} {3}'.format(
                    self.progress, self.ulength//div, self.clength//div, mea),
                    end=end)
