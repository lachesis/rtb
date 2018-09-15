# Remote Token Bucket
Rate limiting service in node using simple line-based socket protocol

# Usage
```SECRET=supersecret node rtb.js```
listens on 127.0.0.1:1337 by default

# Commands

* `UNLOCK <secret>`: authenticate to the server
* `BUCKET <name> <qps> <burst>`: define a new bucket
* `?<name>`: waits until there is a free slot in the bucket, then returns `!name`
* `?`: shorthand for `?<last_used_bucket>`, returns `!`

All commands are sent as `\r\n`-separated strings (similar to Memcached or Redis). Error responses start with `:ERR`. Informational responses start with `:RES` or `!` for the `?` commands.

# Clients

A Python client is included. It was tested with Python 2.7 and Python 3.7. If `tornado` is installed, it will also define an async client using tornado's `IOStream`. See the end of `clients/rtb.py` for a brief test of each client against a local server.
