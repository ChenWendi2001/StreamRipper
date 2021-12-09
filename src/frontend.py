import mitmproxy.http
from mitmproxy import ctx, http

from enum import Enum

class Status(Enum):
    OK = 1
    Error = 2


class Router:

    def request(self, flow: mitmproxy.http.HTTPFlow):
        # only intercept GET requests
        request = flow.request
        if request.method == "GET":
            status,key = self.get_key_from_request(request)
            if status == Status.OK:
                ctx.log.info("OK")
                ctx.log.info(key)
            else:
                ctx.log.info("Error")

    def response(self, flow: mitmproxy.http.HTTPFlow):
        #TODO
        pass

    def http_connect(self, flow: mitmproxy.http.HTTPFlow):  
        # for future use
        pass

    def get_key_from_request(self, request):
        # get file name
        path = request.path
        filename = path[:path.find(".m4s")].split("/")[-1].split("-")[-1]

        # request header (contains referer and range)
        header = request.headers
        referer= header.get("referer", default="no referer")
        range = header.get("range", default="no range").lstrip("bytes=")
        
        #parse
        if referer != "no referer":
            referer = referer[referer.find("BV"):]
            split = [referer.find("?") if referer.find("?")!=-1 else 1000,
                    referer.find("/") if referer.find("/")!=-1 else 1000]
            referer = referer[:min(split)]

        if referer != "no referer" and range != "no range":
            status = Status.OK
        else:
            status = Status.Error
        
        return status,"-".join([referer, filename, range])

addons = [
    Router()
]