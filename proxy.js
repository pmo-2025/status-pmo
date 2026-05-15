const http = require('http');
const net = require('net');
const url = require('url');

const server = http.createServer((req, res) => {
  const opts = url.parse(req.url);
  const proxy = http.request({ hostname: opts.hostname, port: opts.port || 80, path: opts.path, method: req.method, headers: req.headers }, (r) => {
    res.writeHead(r.statusCode, r.headers);
    r.pipe(res);
  });
  req.pipe(proxy);
  proxy.on('error', () => res.end());
});

server.on('connect', (req, sock, head) => {
  const [host, port] = req.url.split(':');
  const s = net.connect(port || 443, host, () => {
    sock.write('HTTP/1.1 200 Connection Established\r\n\r\n');
    s.write(head);
    s.pipe(sock);
    sock.pipe(s);
  });
  s.on('error', () => sock.end());
});

server.listen(3128, '0.0.0.0', () => console.log('Proxy OK puerto 3128'));
