#!/usr/bin/env python

import sys
from os import getcwd
from re import findall, search
from subprocess import check_output, CalledProcessError

try:
    from urllib.request import urlopen, HTTPError
except ImportError:
    from urllib2 import urlopen, HTTPError

from mirrors import RoundTrip, Data

def notUbuntu():
    print("Not an Ubuntu OS")
    sys.exit(1)

try:
    release = check_output("lsb_release -ics 2>/dev/null", shell=True)
except CalledProcessError:
    notUbuntu()
else:
    release = [s.strip() for s in release.decode().split()]

hardware = check_output("uname -m", shell=True).strip().decode()
if release[0] == 'Debian':
    print("Debian is not currently supported")
    sys.exit(1)
elif release[0] != 'Ubuntu':
    notUbuntu()

codename = release[1][0].upper() + release[1][1:]
mirror_list = "http://mirrors.ubuntu.com/mirrors.txt"
try:
    archives = urlopen(mirror_list)
except IOError as err:
    print(("Could not connect to '%s'.\nCheck network connection\n"
           "%s" % (mirror_list, err)))
    sys.exit(1)

print("Got list of mirrors")
archives = archives.read().decode()
urls = findall(r'http://([\w|\.|\-]+)/', archives)
n = 0
avg_rtts = {}
for url in urls:
    ping = RoundTrip(url)
    print("Connecting to %s" % url)
    avg = ping.avgRTT()
    if avg is not False:
        avg_rtts.update({url:avg})
        n += 1
        
print("Tested %d mirrors" % n)
if hardware == 'x86_64':
    hardware = 'amd64'
else:
    hardware = 'i386'

top_num = 5
ranks = sorted(avg_rtts, key=avg_rtts.__getitem__)
info = []
print("Retrieving status information")
for rank in ranks:
    d = Data(rank, codename, hardware)
    data = d.getInfo()
    if data is not False:
        info += [data]

    if len(info) == top_num:
        break

print("\nTop %d mirrors:\n" % top_num)
for i, j in enumerate(info):
    print("%d. %s\n\tLatency: %d ms\n\tStatus: %s\n\tBandwidth: %s\n" % 
          (i + 1, j[0], avg_rtts[j[0]], j[1][0], j[1][1]))

directory = '/etc/apt/'
apt_file = 'sources.list'
try:
    input = raw_input
except NameError:
    pass

def ask(query):
    global input
    answer = input(query)
    return answer

options = "Options:\n[y] for yes\n[n] for no "
def genFile():
    s = "Please select a mirror number from the list (1 - %d) " % top_num
    key = ask(s)
    while True:
        match = search(r'[1-5]', key)
        if match and len(key) == 1:
            key = int(key)
            break
        else:
            print("Not a valid number")
            key = ask(s)

    key = key - 1
    global info
    mirror = info[key][0]
    global archives
    for m in archives.splitlines():
        if mirror in m:
            mirror = m
            break

    found = False
    field1 = ('deb', 'deb-src')
    h = 'http://'
    with open('%s' % directory + apt_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            arr = line.split()
            if not found:
                if (arr and (arr[0] in field1) and
                        (h == arr[1][:7]) and
                        (release[1] in arr[2:])):
                    repo = [arr[1]]
                    found = True
                    continue
            else:
                if (arr and (arr[0] in field1) and
                        (h in arr[1]) and
                        (arr[2] == '%s-security' % (release[1]))):
                    repo += [arr[1]]
                    break
            
        else:
            print("Error finding current repository")
            sys.exit(1)

    lines = ''.join(lines)
    for r in repo:
        lines = lines.replace(r, mirror)

    if getcwd() == directory[0:-1]:
        global options
        query = ("'%(dir)s' is the current directory.\n"
                 "Generating a new '%(apt)s' file will "
                 "overwrite the current file.\n"
                 "You should copy or backup '%(apt)s' before replacing it.\n"
                 "Continue?\n%(opt)s" 
                 % {'dir': directory,
                    'apt': apt_file,
                    'opt': options.replace("Options:\n", "")})
        while True:
            answer = ask(query)
            if answer == 'y':
                break
            elif answer == 'n':
                return
            else:
                query = options
                continue

    try:
        with open(apt_file, 'w') as f:
            f.write(lines)
    except IOError as err:
        print("Unable to write new '%s' file\n%s" % (apt_file, err))
        sys.exit(1)

def genList():
    query = "Generate new '%s' file?\n" % apt_file
    global options
    answer = ask(query + options)
    while True:
        if answer == 'y':
            genFile()
            break
        elif answer == 'n':
            break
        else:
            answer = ask(options)
            continue

genList()

sys.exit(0)