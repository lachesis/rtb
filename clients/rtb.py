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
    def __init__(self, host='127.0.0.1', port=1337, secret=None):
        self.host = host
        self.port = port
        self.secret = secret
        self.socket = None

    def close(self):
        self.socket.close()

    def send(self, msg, raise_error=False):
        logger.debug("> %s", msg)
        if not self.socket:
            self.socket = socket.create_connection((self.host, self.port), timeout=10)
            if self.secret:
                self.send("UNLOCK {}".format(self.secret), raise_error=True)
        self.socket.send((msg + u"\r\n").encode('utf-8'))
        resp = self.socket.recv(1024).decode('utf-8').strip()
        logger.debug("< %s", resp)
        if resp.startswith(':ERR') and raise_error:
            raise ValueError("Error from RTB: %r" % resp)
        return resp

    def define(self, bucket, qps, burst):
        self.send(u"BUCKET {} {} {}".format(bucket, qps, burst), raise_error=True)

    def block(self, bucket):
        resp = self.send(u"?{}".format(bucket), raise_error=True)
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
        def __init__(self, host='127.0.0.1', port=1337, secret=None):
            self.host = host
            self.port = port
            self.secret = secret
            self.client = tornado.tcpclient.TCPClient()
            self.stream = None

        def close(self):
            if self.stream:
                self.stream.close()

        @gen.coroutine
        def send(self, msg, raise_error=False):
            logger.debug("> %s", msg)
            if not self.stream:
                self.stream = yield self.client.connect(self.host, self.port)
                if self.secret:
                    yield self.send("UNLOCK {}".format(self.secret), raise_error=True)
            yield self.stream.write((msg + u"\r\n").encode('utf-8'))
            resp = yield self.stream.read_until(b"\r\n")
            resp = resp.decode('utf-8').strip()
            logger.debug("< %s", resp)
            if resp.startswith(':ERR') and raise_error:
                raise ValueError("Error from RTB: %r" % resp)
            raise gen.Return(resp)

        @gen.coroutine
        def define(self, bucket, qps, burst):
            yield self.send(u"BUCKET {} {} {}".format(bucket, qps, burst), raise_error=True)

        @gen.coroutine
        def block(self, bucket):
            resp = yield self.send(u"?{}".format(bucket), raise_error=True)
            if resp == '!' + bucket:
                raise gen.Return(True)
            logger.warning("Unrecognized response: %r", resp)
            raise gen.Return(False)


if __name__ == '__main__':
    import logging; logging.basicConfig(level=logging.DEBUG)
    import uuid

    # Test sync
    if 0:
        bucket_name = 'sync_' + str(uuid.uuid4())
        rtb = RemoteTokenBucket()
        rtb.define(bucket_name, 2, 4)
        for i in range(20):
            print(i, time.time(), rtb.block(bucket_name))
        time.sleep(2)
        for i in range(5):
            print(i, time.time(), rtb.block(bucket_name))
        rtb.close()

    # Test tornado
    import tornado
    from tornado import gen
    @gen.coroutine
    def test_tornado():
        bucket_name = 'async_' + str(uuid.uuid4())
        trtb = TornadoRemoteTokenBucket()
        trtb.define(bucket_name, 5, 2)
        for i in range(30):
            r = yield trtb.block(bucket_name)
            print(i, time.time(), r)
        yield gen.sleep(2)
        for i in range(4):
            r = yield trtb.block(bucket_name)
            print(i, time.time(), r)
        trtb.close()
    tornado.ioloop.IOLoop.current().run_sync(test_tornado)
