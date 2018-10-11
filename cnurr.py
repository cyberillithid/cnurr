#!/usr/env/python3
# -*- coding: utf-8 -*-
"""Main file of CNURR -- the old EtherPad crawler.

(c) c.i., 2018
"""
__version__ = '0.1'
from urllib import request, parse
import re
import sys
from typing import Optional
import http.client

class Cnurr:
    """Main crawler class"""
    def __init__(self, hostname) -> None:
        """Constructor"""
        self.domain = 'https://' + hostname
        self.hostname = hostname
        self.cookie = None
    def _fetch(self, addr: str) -> str:
        """Fetches requested addr from current domain"""
        req = request.Request(self.domain + addr, headers={'Cookie': self.cookie})
        return request.urlopen(req).read().decode('utf-8')
    def get_padlist(self) -> list:
        """Returns list of all now-existing pads"""
        page = self._fetch('/ep/padlist/all-pads')
        return re.findall(r'"title first"><a href="/(.*)">(.*)</a', page)
    def max_rev(self, pad: str) -> Optional[int]:
        """Fetches maximum revision of the pad"""
        page = self._fetch('/ep/pad/view/' + pad + '/rev.0')
        mach = re.findall(r'"totalRevs":([0-9]*),', page)
        if not mach:
            return None
        return int(mach[0])
    def fetch_pad(self, pad: str, maxrev: int):
        """Fetches selected pad changeset from 0 to maxrev"""
        print(pad, maxrev)
        granularity = ((maxrev)//100) + 1
        link = '/ep/pad/changes/' + pad
        link += '?s=0&g=' + str(granularity)
        json = self._fetch(link)
        return json
    def save_pads(self, savedir: str, pads: Optional[list] = None) -> Optional[list]:
        """Saves all pads in selected dir. If `pads` is None, saves all pads).
        Returns pads that were impossible to recover (i. e., have password protection)"""
        if pads is None:
            pads = self.get_padlist()
        forbidden = []
        listjson = []
        for (pad, name) in pads:
            maxrev = self.max_rev(pad)
            if maxrev is None:
                forbidden.append(pad)
                continue
            listjson.append('{"file": "' + pad + '.json", "name": "' + name + '"}')
            padfile = open(savedir + '/' + pad + '.json', 'w', encoding='utf-8')
            json = self.fetch_pad(pad, maxrev)
            padfile.write(json)
            padfile.close()
        listfile = open(savedir + '/__INDEX__.json', 'w', encoding='utf-8')
        listfile.write('[' + ', '.join(listjson) + ']')
        listfile.close()
        if not forbidden:
            return None
        return forbidden
    def auth(self, username: str, password: str) -> None:
        """Authorizes and creates valid cookies"""
        conn = http.client.HTTPSConnection(self.hostname)
        conn.request('GET', '')
        redir_resp = conn.getresponse()
        redir_loc = redir_resp.getheader('Location').split('/')
        conn_team = http.client.HTTPSConnection(redir_loc[2])
        conn_team.request('GET', '/' + redir_loc[3])
        cookie_sets = conn_team.getresponse().getheader('Set-Cookie')
        cookie_list = re.findall(r'ES=[0-9a-f]*; ', cookie_sets)
        cookie_list += re.findall(r'ET=[0-9a-f]*; ', cookie_sets)
        self.cookie = ''.join(cookie_list)
        post_data = {'email': username, 'password': password}
        datum = parse.urlencode(post_data).encode('utf-8')
        req = request.Request(self.domain + '/ep/account/sign-in?undefined',
                              headers={'Cookie': self.cookie})
        request.urlopen(req, data=datum) # res -> 'ASIE=F'
        self.cookie += 'ASIE=F'
        return
def main():
    """Default executable method. Used as %domain% %username% %password%"""
    cnurr = Cnurr(sys.argv[1])
    cnurr.auth(sys.argv[2], sys.argv[3])
    cnurr.save_pads('pads')

if __name__ == '__main__':
    # run as standalone executable
    main()
