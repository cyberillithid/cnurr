"""Main file of etherpad crawler"""
# some bin/bash/whateva & utf-8
import urllib.request as request
import re

cookie = ''

def get_cookies(domain):
    """Authorization magic (in the future)"""
    global cookie
    # req = request.Request(team_domain + '/', headers={'Cookie': cookies})
    if domain is None:
        raise ValueError
    cookie_file = open('cookie.txt', 'r')
    cookie = cookie_file.read()
    cookie_file.close()
    return cookie

def main():
    """Main function body"""
    global cookie
    team_domain = 'https://rpgpl.piratenpad.de'
    get_cookies(team_domain)
    # prefs=%7B%22fullWidth%22%3Afalse%2C%22hideSidebar%22%3Afalse%2C%22viewZoom%22%3A100%2C
    # %22isFullWidth%22%3Afalse%7D;
    req = request.Request(team_domain + '/ep/padlist/all-pads', headers={'Cookie': cookie})
    padlist_page = request.urlopen(req).read().decode('utf-8')
    padlist = re.findall(r'"title first"><a href="/(.*)"', padlist_page)
    for pad in padlist:
        print('Saving ' + pad)
        save_pad(team_domain, pad)

def get_rev_count(link):
    """Fetch last revision from Admin->Recover pad text interface"""
    global cookie
    req = request.Request(link, headers={'Cookie': cookie})
    admin_page = request.urlopen(req).read().decode('utf-8')
    rev_arr = re.findall(r'value="([0-9]*)" name="revNum"', admin_page)
    if len(rev_arr) != 1:
        raise IOError
    return int(rev_arr[0])

def fetch_changeset(domain, pad, start, granularity):
    """Fetches changeset"""
    global cookie
    link = domain + '/ep/pad/changes/' + pad 
    link += '?s=' + str(start) + '&g=' + str(granularity)
    req = request.Request(link, headers={'Cookie': cookie})
    json = request.urlopen(req).read().decode('utf-8')
    return json

def save_pad(domain, pad):
    """Save pad backups"""
    max_rev = get_rev_count(domain+'/ep/admin/recover-padtext?localPadId='+pad)
    jsons = []
    last = 0
    while last < max_rev:
        granularity = (max_rev - last)//100
        if granularity == 0:
            granularity = 1
        jsons.append(fetch_changeset(domain, pad, last, granularity))
        last += (granularity * 100)
    padfile = open('pads/' + pad + '.json', 'w', encoding='utf-8')
    padfile.write('[' + ','.join(jsons) + ']')
    padfile.close()

main()
