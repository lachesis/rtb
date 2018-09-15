#!/usr/bin/env python
# Python client for Remote Token Bucket
# Works in Py2 or Py3
# Defines sync class RemoteTokenBucket with no deps (beyond stdlib)
# Defines async classTornadoRemoteTokenBucket if tornado is installed
from __future__ import print_function
import logging
import socket
import time
logger = logging.getLogger(__name__)

class RemoteTokenBucket(object):
    def __init__(self, host='127.0.0.1', port=1337):
        self.host = host
        self.port = port
        self.socket = socket.create_connection((self.host, self.port), timeout=10)
    def close(self):
        self.socket.close()
    def define(self, bucket, qps, burst):
        self.socket.send(u"BUCKET {} {} {}\r\n".format(bucket, qps, burst).encode('utf-8'))
        resp = self.socket.recv(1024).decode('utf-8').strip()
        if resp.startswith(':ERR'):
            logger.warning("Error response: %r", resp)
            return False
        return True
    def block(self, bucket):
        self.socket.send(u"?{}\r\n".format(bucket).encode('utf-8'))
        resp = self.socket.recv(1024).decode('utf-8').strip()
        if resp == '!' + bucket:
            return True
        logger.warning("Unrecognized response: %r", resp)
        return False

try:
    import tornado
    import tornado.tcpclient
    from tornado import gen
except ImportError:
    pass
else:
    class TornadoRemoteTokenBucket(object):
        def __init__(self, host='127.0.0.1', port=1337):
            self.host = host
            self.port = port
            self.client = tornado.tcpclient.TCPClient()
            self.stream = None
        def close(self):
            if self.stream:
                self.stream.close()
        @gen.coroutine
        def define(self, bucket, qps, burst):
            if not self.stream:
                self.stream = yield self.client.connect(self.host, self.port)
            yield self.stream.write(u"BUCKET {} {} {}\r\n".format(bucket, qps, burst).encode('utf-8'))
            resp = yield self.stream.read_until(b"\r\n")
            resp = resp.decode('utf-8')
            if resp.startswith(':ERR'):
                logger.warning("Error response: %r", resp)
            raise gen.Return(resp)
        @gen.coroutine
        def block(self, bucket):
            if not self.stream:
                self.stream = yield self.client.connect(self.host, self.port)
            yield self.stream.write(u"?{}\r\n".format(bucket).encode('utf-8'))
            resp = yield self.stream.read_until(b"\r\n")
            resp = resp.decode('utf-8')
            if resp.startswith(':ERR'):
                logger.warning("Error response: %r", resp)
                raise gen.Return(False)
            raise gen.Return(True)


if __name__ == '__main__':
    import logging; logging.basicConfig(level=logging.DEBUG)

    # Test sync
    if 0:
        rtb = RemoteTokenBucket()
        rtb.define('hello', 2, 4)
        for i in range(20):
            print(i, time.time(), rtb.block('hello'))
        time.sleep(2)
        for i in range(5):
            print(i, time.time(), rtb.block('hello'))
        rtb.close()

    # Test tornado
    import tornado
    from tornado import gen
    @gen.coroutine
    def test_tornado():
        trtb = TornadoRemoteTokenBucket()
        trtb.define("goodbye", 5, 2)
        for i in range(30):
            r = yield trtb.block('goodbye')
            print(i, time.time(), r)
        yield gen.sleep(2)
        for i in range(4):
            r = yield trtb.block('goodbye')
            print(i, time.time(), r)
        trtb.close()
    tornado.ioloop.IOLoop.current().run_sync(test_tornado)
