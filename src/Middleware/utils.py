import asyncio
import copy
import pickle
import re

import requests
from mitmproxy import http

from utils import printError, printInfo, printWarn

from .P2P.client import download


def changeRequest(request, start, end, ori_range):
    """[summary]
    NOTE: [start, end] are ABSOLUTE index
    for request, MODIFY THE FOLLOWING
        request.headers.range ("bytes={}-{}")
    """
    new_request = copy.deepcopy(request)
    new_request.headers["range"] = f"bytes={start}-{end}"
    new_request.headers["ori-range"] = "{},{}".format(*ori_range)
    return new_request


def extractResponse(response, start, end):
    """[summary]
    NOTE: [start, end] are ABSOLUTE index
    for response, MODIFY THE FOLLOWING
      content-length, content-range
    """
    new_response = copy.deepcopy(response)
    new_response.headers["content-length"] = str(end - start + 1)
    low, high, length = re.search(
        "(\d+)-(\d+)/(\d+)", response.headers["content-range"]).groups()
    new_response.headers["content-range"] = f"bytes {start}-{end}/{length}"
    new_response.headers["debug"] = "Reorganization"
    new_response.content = response.content[
        start - int(low):end + 1 - int(low)]
    printError(
        start < int(low) or end > int(high),
        f"incorrect range {start}, {end}, {low}, {high}")
    printError(
        len(new_response.content) != end - start + 1,
        "incorrect content length")
    return new_response


def catResponse(this, response):
    """[summary]
    NOTE: concate new response to this
    """
    this.content += response.content
    l0, h0, len0 = map(int, re.search(
        "(\d+)-(\d+)+/(\d+)", this.headers["content-range"]).groups())
    l1, h1, len1 = map(int, re.search(
        "(\d+)-(\d+)+/(\d+)", response.headers["content-range"]).groups())
    printError(
        len0 != len1 or h0 + 1 != l1,
        "concate different responses")
    this.headers["content-length"] = str(h1 - l0 + 1)
    this.headers["content-range"] = f"{l0}-{h1}/{len0}"
    this.headers["debug"] = "Reorganization"


def peerDownload(key, target_ip):
    result = asyncio.run(
        download(key, target_ip))
    printInfo("\033[43m block hit \033[0m")
    return result


def peerDelegate(request, target_ip):
    url = request.pretty_url
    headers = request.headers.fields
    headers = {k.decode(): v.decode() for k, v in headers}
    headers["scheduler"] = "True"

    try:
        response = requests.get(
            url, headers=headers,
            proxies={"https": target_ip + ":8080"},
            verify=False, timeout=4)

        # download data
        result = http.Response.make(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,)
        result = pickle.dumps(result)

    except Exception as e:
        printWarn(e)
        result = ""

    return result
