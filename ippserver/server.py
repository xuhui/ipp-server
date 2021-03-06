from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from StringIO import StringIO
import socket
import threading
import SocketServer
import time
import logging
import os.path

from . import request
from .http_transport import HttpTransport, ConnectionClosedError


def local_file_location(filename):
	return os.path.join(os.path.dirname(__file__), 'data', filename)


class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler):
	def handle(self):
		try:
			self._handle()
		except Exception:
			logging.exception('Error handling request')

	def _handle(self):
		http = HttpTransport(self.rfile, self.wfile)
		try:
			http.recv_headers()
		except ConnectionClosedError:
			logging.debug('Handled request which was immediately closed')
			return

		try:
			if http.method == 'POST':
				self.handle_ipp(http)
			elif http.method == 'GET':
				self.handle_www(http)
			else:
				raise ValueError(http.method)
		except Exception:
			logging.exception('Failed to parse')
			http.send_headers(status='500 Server error', content_type='text/plain')
			with open(local_file_location('error.txt'), 'r') as error_file:
				http.send_body(error_file)

		http.close()  # no content-length header and no chunked response

	def handle_www(self, http):
		if http.path == '/':
			http.send_headers(status='200 OK', content_type='text/plain')
			with open(local_file_location('homepage.txt'), 'r') as homepage_file:
				http.send_body(homepage_file)
		elif http.path.endswith('.ppd'):
			http.send_headers(status='200 OK', content_type='text/plain')
			ppd_file_text = self.server.behaviour.ppd.text()
			http.send_body(StringIO(ppd_file_text))
		else:
			http.send_headers(status='404 Not found', content_type='text/plain')
			with open(local_file_location('404.txt'), 'r') as homepage_file:
				http.send_body(homepage_file)


	def handle_ipp(self, http):
		ipp_request_file = http.recv_body()
		ipp_request = request.IppRequest.from_file(ipp_request_file)

		if self.server.behaviour.expect_page_data_follows(ipp_request):
			http.send_headers(status='100 Continue', content_type='application/ipp')
			postscript_file = http.recv_body()
		else:
			http.send_headers(status='200 OK', content_type='application/ipp')
			postscript_file = None

		ipp_response = self.server.behaviour.handle_ipp(ipp_request, postscript_file)
		http.send_body(StringIO(ipp_response.to_string())) # XXX inefficient


class ThreadedTCPServer(SocketServer.ThreadingTCPServer):
	allow_reuse_address = True
	def __init__(self, address, request_handler, behaviour):
		self.behaviour = behaviour
		SocketServer.ThreadingTCPServer.__init__(self, address, request_handler)  # old style class!

def wait_until_ctrl_c():
	try:
		while True:
			time.sleep(300)
	except KeyboardInterrupt:
		return

def run_server(server):
	logging.info('Listening on %r', server.server_address)
	server_thread = threading.Thread(target=server.serve_forever)
	server_thread.daemon = True
	server_thread.start()
	wait_until_ctrl_c()
	logging.info('Ready to shut down')
	server.shutdown()
