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
