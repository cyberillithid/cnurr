#!/usr/env/python3
# -*- coding: utf-8 -*-
"""Main file of CNURR -- the old-EtherPad crawler.

(c) c.i., 2018
"""
__version__ = '0.1'
from urllib import request, parse, error
import re
import sys
import argparse
from typing import Optional
import http.client
import shlex
import ssl
import os

class CnurrDomain:
    """Old EtherPad domain class"""
    def __init__(self, domain: str) -> None:
        """Constructor for domain"""
        self.domain = domain
        loc = domain.split('/')
        if loc[0] == 'http:':
            self.use_ssl = False
        else:
            self.use_ssl = True
        self.hostname = loc[2]
        self._make_cookie()
    def _make_cookie(self) -> None:
        """Creates cookies, required by old EtherPad"""
        ctx = ssl._create_unverified_context()
        if self.use_ssl:
            conn = http.client.HTTPSConnection(self.hostname, context=ctx)
        else:
            conn = http.client.HTTPConnection(self.hostname)
        conn.request('GET', '')
        redir_resp = conn.getresponse()
        cookie_0 = redir_resp.getheader('Set-Cookie')
        if cookie_0 is not None:
            cookie_sets = cookie_0
        else:
            cookie_sets = ''
        redir = redir_resp.getheader('Location')
        if redir is not None:
            redir_loc = redir_resp.getheader('Location').split('/')
            if redir_loc[0] == 'https:':
                conn_team = http.client.HTTPSConnection(redir_loc[2], context=ctx)
            else:
                conn_team = http.client.HTTPConnection(redir_loc[2])
            conn_team.request('GET', '/' + '/'.join(redir_loc[3:]))
            conn_resp = conn_team.getresponse()
            cookie_0 = conn_resp.getheader('Set-Cookie')
            if cookie_0 is not None:
                cookie_sets += cookie_0
            redir = conn_resp.getheader('Location')
        cookie_list = re.findall(r'ES=[0-9a-f]*; ', cookie_sets)
        cookie_list += re.findall(r'ET=[0-9a-f]*; ', cookie_sets)
        self.cookie = ''.join(cookie_list)
    def _fetch(self, addr: str) -> str:
        """Fetches requested addr from current domain"""
        ctx = ssl._create_unverified_context()
        req = request.Request(self.domain + addr, headers={'Cookie': self.cookie})
        return request.urlopen(req, context=ctx).read().decode('utf-8')
    def fetch_pad(self, pad: str, startrev: int, granularity: int) -> str:
        """Fetches selected pad changeset from startrev with granularity"""
        print(pad, startrev, ', g =', granularity)
        # granularity = ((maxrev - startrev)//100) + 1
        link = '/ep/pad/changes/' + pad
        link += '?s=' + str(startrev) + '&g=' + str(granularity)
        json = self._fetch(link)
        return json
    def fetch_chat(self, pad: str, fin: int = 65536000) -> str:
        """Saves pad chat history from start (#0) to fin (#fin) messages"""
        link = '/ep/pad/chathistory?start=0&end=' + str(fin) + '&padId=' + str(pad)
        json = self._fetch(link)
        return json
    def max_rev(self, pad: str) -> Optional[int]:
        """Fetches maximum revision of the pad"""
        page = self._fetch('/ep/pad/view/' + pad + '/rev.0')
        mach = re.findall(r'"totalRevs":([0-9]*),', page)
        if not mach:
            return None
        return int(mach[0])

class CnurrTeamDomain(CnurrDomain):
    """Old EtherPad team domain class"""
    def __init__(self, domain: str, username: str, password: str) -> None:
        super().__init__(domain)
        # -- auth --
        ctx = ssl._create_unverified_context()
        post_data = {'email': username, 'password': password}
        datum = parse.urlencode(post_data).encode('utf-8')
        req = request.Request(self.domain + '/ep/account/sign-in?undefined',
                              headers={'Cookie': self.cookie})
        request.urlopen(req, data=datum, context=ctx) # res -> 'ASIE=F'
        self.cookie += 'ASIE=F'
    def get_padlist(self) -> list:
        """Returns list of all now-existing pads"""
        page = self._fetch('/ep/padlist/all-pads')
        return re.findall(r'"title first"><a href="/(.*)">(.*)</a', page)

def create_index(savedir: str, domain: str, padlist: list) -> list:
    """Creates INDEX file with titles of pads"""
    listjson = ['{"file": "' + pad + '", "name": "' + name + '"}' for (pad, name) in padlist]
    listfile = open(savedir + '/' + domain + '.INDEX.json', 'w', encoding='utf-8')
    listfile.write('[' + ', '.join(listjson) + ']')
    listfile.close()
    return [pad for (pad, name) in padlist]

def main(inargs=None):
    """Default executable method. Used as %domain%"""
    parser = argparse.ArgumentParser(description='Save EtherPad. ' +
                                     'If no args specified, read from input.txt')
    parser.add_argument('-f', '--fine', action='store_true',
                        help='Saves each revision of document (by default - only 100 integral revs)'
                       )
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Additionally process all of referred pad links on the same domain')
    parser.add_argument('-t', '--team', nargs=2, metavar=('EMAIL', 'PASSWORD'),
                        help='Login to team pad site with EMAIL and PASSWORD and download all pads')
    parser.add_argument('-o', '--outdir', default='pads')
    parser.add_argument('domain', help='Pad/team site address')
    parser.add_argument('pads', nargs='*', metavar='pad', help='Pad names')
    args = parser.parse_args(inargs)
    print(args)
    if args.team is not None:
        domain = CnurrTeamDomain(args.domain, args.team[0], args.team[1])
        if not args.pads:
            args.pads = create_index(args.outdir, domain.hostname, domain.get_padlist())
    else:
        domain = CnurrDomain(args.domain)
    savedir = args.outdir + '/' + domain.hostname
    if not os.path.exists(savedir):
        os.makedirs(savedir)
    save_all_pads(args, domain, savedir, args.pads)

def save_all_pads(args, domain, savedir, padlist, oldpadlist = []) -> list:
    """Saves all pads; even recursively"""
    forbidden = []
    rec = []
    for pad in padlist:
        try:
            maxrev = domain.max_rev(pad)
        except error.HTTPError:
            print('Error on', pad)
            maxrev = None
        if maxrev is None:
            forbidden.append(pad)
            continue
        if args.fine:
            jsons = []
            for i in range(0, maxrev, 100):
                jsons.append(domain.fetch_pad(pad, i, 1))
            json = '[' + ', '.join(jsons) + ']'
        elif args.recursive:
            json = domain.fetch_pad(pad, 0, (maxrev)+1)
        else:
            json = domain.fetch_pad(pad, 0, (maxrev // 100) + 1)
        padfile = open(savedir + '/' + pad + '.json', 'w', encoding='utf-8')
        padfile.write(json)
        padfile.close()
        chatfile = open(savedir + '/' + pad + '.chat.json', 'w', encoding='utf-8')
        chatjson = domain.fetch_chat(pad)
        chatfile.write(chatjson)
        chatfile.close()
        if args.recursive:
            reccur = re.findall(domain.domain + r'/([A-Za-z0-9._\-]*)', json)
            rec += reccur
    prevset = set(padlist) | set(oldpadlist)
    setrec = set(rec) - prevset
    if setrec:
        save_all_pads(args, domain, savedir, list(setrec), list(prevset))
    return forbidden

if __name__ == '__main__':
    # run as standalone executable
    if len(sys.argv) < 2:
        print('No args, reading from input.txt')
        argf = open('input.txt')
        for line in argf.readlines():
            if line[0] != '#':
                main(shlex.split(line))
        argf.close()
    else:
        main()
