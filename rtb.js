// Remote tocken bucket using socket protocol
// Usage: node rtb.js
// Listens on 127.0.0.1:1337
// Protocol (telnet, \r\n-separated commands, similar to redis/memcached):
// UNLOCK <secret> -> authenticate to the service, using secret from env var SECRET
// BUCKET <name> <qps> <burst> -> define a new bucket
// ?<name> -> wait for bucket to be ready. sends "!<name>" when bucket is ready
// ? -> shorthand for ?<last_bucket_used>, sends "!" when bucket is ready
// Example client session:
// BUCKET test 1 2
// ?test
// ?
var net = require('net');

var buckets = {}

class Bucket {
  constructor(name, qps, burst) {
    this.name = name
    this.qps = qps
    this.burst = burst
    this.value = 0
    this.waiting = []
    this.interval = null
    this.shutdown_promise_resolve = null
  }
  tick() {
    if (this.interval === null) {
      console.warn("Interval not registered")
    }
    if (this.waiting.length) {
      this.waiting.shift()()
    }
    else {
      if (this.shutdown_promise_resolve)
        this.shutdown_promise_resolve()  // resolve the shutdown promise
      let val = this.value + 1
      if (val <= this.burst)
        this.value = val
    }
  }
  block() {
    if (this.interval === null) {
      console.warn("Interval not registered")
    }
    if (this.shutdown_promise_resolve) {
      return Promise.reject("Shutting down")
    }
    else if (this.value > 0) {
      this.value--
      return Promise.resolve()
    }
    else {
      return new Promise((resolve, reject)=>this.waiting.push(resolve))
    }
  }
  register() {
    // Register this bucket with the global list of buckets
    // Start the interval tick
    if (buckets[this.name])
      throw "Bucket already registered";
    buckets[this.name] = this
    this.interval = setInterval(this.tick.bind(this), 1000/this.qps)
  }
  shutdown() {
    // Stop accepting new waiters
    // Wait for all waiters to finish
    // Clear tick interval and delete bucket from registry
    return new Promise((resolve, reject)=>{
      this.shutdown_promise_resolve = resolve
    }).then(()=>{
      clearInterval(this.interval)
      this.interval = null
      delete buckets[this.name]
    })
  }
}

var server = net.createServer(function(socket) {
  var lastBucket = null;
  var authenticated = false;
  if (!process.env.SECRET)
    authenticated = true;
  socket.on('data', async function(data){
    var text = data.toString('utf8').trim();
    if (text.startsWith("?") && text.length > 1) {
      lastBucket = text.replace("?", "");
    }
    if (text.startsWith('UNLOCK ') && process.env.SECRET) {
      if (text == 'UNLOCK ' + process.env.SECRET) {
        socket.write(":RES unlocked\r\n")
        authenticated = true;
      } else {
        socket.write(":ERR invalid secret\r\n")
      }
      return;
    }
    if (!authenticated)
      socket.write(":ERR must authenticate with UNLOCK <secret>\r\n");
    else if (text.startsWith("?")) {
      if (!lastBucket) {
        socket.write(":ERR no last bucket specified\r\n")
      }
      else if (!buckets[lastBucket]) {
        socket.write(":ERR bucket does not exist\r\n")
      }
      else {
        await buckets[lastBucket].block()
        socket.write(text.replace("?", "!") + "\r\n")
      }
    }
    else if (text.startsWith("BUCKET ")) {
      var match = /BUCKET ([^\s]+) ([0-9.]+) ([0-9]+)/.exec(text);
      try {
        new Bucket(match[1], parseFloat(match[2]), parseInt(match[3])).register()
        socket.write(":RES registered\r\n")
      }
      catch (e) {
        socket.write(":ERR cannot register, " + e + "\r\n")
      }
    }
    else {
      socket.write(":ERR unknown command\r\n");
    }
  });
});
server.on('error', console.error);
server.listen(1337, '127.0.0.1');
console.log("Running on 127.0.0.1:1337")

function testBucket() {
  new Bucket("test", 1, 2).register()
  setTimeout(()=>{
    buckets['test'].block().then((x)=>console.log(1))
    buckets['test'].block().then((x)=>console.log(2))
    buckets['test'].block().then((x)=>console.log(3))
    buckets['test'].block().then((x)=>console.log(4))
    buckets['test'].block().then((x)=>console.log(5))
    buckets['test'].block().then((x)=>console.log(6))
    buckets['test'].block().then((x)=>console.log(7))
    buckets['test'].block().then((x)=>console.log(8))
    buckets['test'].block().then((x)=>console.log(9))
    buckets['test'].block().then((x)=>console.log(10))
    buckets['test'].shutdown()
  }, 5000)
}
