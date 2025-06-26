from http.server import HTTPServer, SimpleHTTPRequestHandler
import ssl

PORT = 4444

class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Hello, world!\n This is your flag: GRAZIEDARIOGRAZIEDARIOGRAZIEDP1=")

httpd = HTTPServer(('0.0.0.0', PORT), CustomHandler)

context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile='server-cert.pem', keyfile='server-key.pem')
context.load_verify_locations(cafile='ca-cert.pem')
context.verify_mode = ssl.CERT_OPTIONAL

# 💡 Only advertise HTTP/1.1
context.set_alpn_protocols(['http/1.1'])

httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

print(f"Serving HTTPS (HTTP/1.1) on port {PORT}")
httpd.serve_forever()
