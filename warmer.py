#!/usr/bin/env python3
"""
origin repo https://gist.github.com/hn-support/bc7cc401e3603a848a4dec4b18f3a78d

Warm the caches of your website by crawling each page defined in sitemap.xml.
To use, download this file and make it executable. Then run:
./warmer.py --threads 4 --file /data/web/public/sitemap.xml -v or 
./warmer.py --threads 4 --url https://site.com/sitemap.xml
"""
import argparse
import multiprocessing.pool as mpool
import os.path
import re
import sys
import time
import requests
import subprocess
# import urllib.request
from urllib.request import urlopen, Request

results = []
start = time.time()
count = 1
i = 1


def parse_options():
    parser = argparse.ArgumentParser(
        description="""Cache crawler based on a sitemap.xml file/url""")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help='The sitemap xml file', type=str)
    group.add_argument('-u', '--url', help='The sitemap xml url', type=str)
    parser.add_argument('-d', '--oldDomain', help='The old domain to replace', type=str)
    parser.add_argument('-n', '--newDomain', help='The new domain to replace with', type=str)
    parser.add_argument('-t', '--threads', help='How many threads to use',
                        default=10, required=False, type=int)
    parser.add_argument('-o', '--output', help='The filename for output results',
                        default='404.txt', required=False, type=str)
    parser.add_argument('-v', '--verbose', help='Be more verbose',
                        action='store_true', default=False)

    args = parser.parse_args()
    if args.file and not os.path.isfile(args.file):
        parser.error('Could not find sitemap file %s' % args.file)
    return args


def crawl_url(url, outputFile, outputFileOk, verbose=False):
    global count, i
    if verbose:
        # print("Crawling {}".format(url))
        progress = i*100/count
        i += 1
        sys.stdout.write(str(round(progress)) + '%' + '\r')

    a = requests.get(url, headers={"user-agent": "SitemapCacheWarmer"})
    if a.status_code == 404:
        outputFile.write("404: %s\n" % url)
    else:
        outputFileOk.write("%s: %s\n" % (a.status_code, url))
    return {'exit': 0 if a.ok() else 1, 'out': a.text, 'url': url}


def make_results():
    errcount = 0
    exec_time = format(time.time() - start, '.4f')
    for item in results:
        if item['exit'] == 0:
            continue
        else:
            errcount += 1
            print("Errors detected in %s:\n%s\n" % (item['url'], item['out']))
            print("=" * 50)
    if errcount == 0:
        print("All DONE! - All urls are warmed! - done in %s " % exec_time)
        return 0
    else:
        print("%d Errors detected! - done in %ss" % (errcount, exec_time))
        return 1


def get_sitemap_urls(filename, url):
    if url:
        sitemap = urlopen(Request(filename, headers={'User-Agent': 'Mozilla'})).read()
        if len(re.findall('<sitemap>', sitemap.decode("utf-8"))) > 0:
            urls = re.findall('<loc>(.*?)</loc>?', sitemap.decode("utf-8"))
            return multipage_sitemap(urls)
        else:
            return re.findall('<loc>(.*?)</loc>?', sitemap.decode("utf-8"))
    else:
        with open(filename) as fh:
            sitemap = fh.read()
            if len(re.findall('<sitemap>', sitemap)) > 0:
                urls = re.findall('<loc>(.*?)</loc>?', sitemap)
                return multipage_sitemap(urls)
            else:
                return re.findall('<loc>(.*?)</loc>?', sitemap)


def multipage_sitemap(urls):
    # urls = re.findall('<loc>(.*?)</loc>?', sitemap.decode("utf-8"))
    tmp = []
    for loc in urls:
        sitemap1 = urlopen(Request(loc, headers={'User-Agent': 'Mozilla'})).read()
        tmp.extend(re.findall('<loc>(.*?)</loc>?',
                              sitemap1.decode("utf-8")))
    return tmp


def callback(output):
    results.append(output)


def main():
    global count
    args = parse_options()
    if args.file:
        sitemap_urls = get_sitemap_urls(args.file, 0)
    else:
        sitemap_urls = get_sitemap_urls(args.url, 1)

    if args.verbose:
        print("Crawling {} urls with {} threads\n[Please Wait!]".format(
            len(sitemap_urls), args.threads))
        print("=" * 50)

    count = len(sitemap_urls)
    pool = mpool.ThreadPool(args.threads)
    domain = args.oldDomain
    newDomain = args.newDomain
    outputFile = open(args.output,"w+")
    outputFileOk = open('200-302.txt', "w+")
    for url in sitemap_urls:
        url = url.replace(domain, newDomain)
        pool.apply_async(crawl_url, args=(
            url, outputFile, outputFileOk, args.verbose), callback=callback)
    pool.close()
    pool.join()
    outputFile.close()
    outputFileOk.close()
    sys.exit(make_results())


if __name__ == "__main__":
    main()
