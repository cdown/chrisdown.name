#!/usr/bin/env python

import lxml.html
import os
import yaml
import requests

def _atScriptDir(path):
    return os.path.join(os.path.dirname(__file__), path)

config = yaml.safe_load(open(_atScriptDir("../_config.yml")))

def _atSiteRoot(path):
    return os.path.join(_atScriptDir(os.path.join("..", config["destination"])))

def getHTMLFiles():
    for root, dirnames, filenames in os.walk(_atSiteRoot(".")):
        for filename in filenames:
            filename = os.path.join(root, filename)
            if filename.endswith(".htm") or filename.endswith(".html"):
                yield filename

def getLinks(filename):
    with open(filename) as f:
        root = lxml.html.parse(f)
        urls = root.xpath("//a/@href")
        return set(urls)

def testLinksAreValid():
    filenames = getHTMLFiles()
    seen = []

    for filename in filenames:
        urls = getLinks(filename)
        for url in urls:
            try:
                if url in seen:
                    continue
                r = requests.head(url)
                assert r.status_code in (200, 201, 301, 302), "Got status code %d for %s" % (r.status_code, url)
                seen.append(url)
            except requests.exceptions.MissingSchema:
                if url.startswith("/"):
                    assert os.path.exists(_atSiteRoot(url.lstrip("/"))), "Missing: %s" % url
                else:
                    assert os.path.exists(os.path.join(os.path.dirname(filename), url)), "Missing: %s" % url
