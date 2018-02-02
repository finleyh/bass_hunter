#!/usr/bin/env python
#FH 
import SimpleHTTPServer
import SocketServer
import os


os.chdir('ss')


HOST , PORT = "0.0.0.0", 443

def main():
	Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
	httpd = SocketServer.TCPServer((HOST, PORT),Handler)
	print "serving up on port" , PORT

	httpd.serve_forever()


if __name__=="__main__":
	main()	
