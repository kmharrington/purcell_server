## Echo server program
# import socket

# HOST = 'localhost'      # Symbolic name meaning all available interfaces
# PORT = 1423             # Arbitrary non-privileged port
# eqLoc = 0
# dcLoc = 0
# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# s.bind((HOST, PORT))
# s.listen(1)
# while 1:
#     print 'Listening for Connection'
#     conn, addr = s.accept()
#     print 'Connected by', addr
#     while 1:
#         data = conn.recv(1024)
#         if not data: break
#
#         conn.sendall(res)
#     conn.close()
#     print 'Connection Closed'
#

import asynchat
import asyncore
import socket

class proxy_server(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.there = (host, port)
        here = ('localhost', 1420)
        self.bind(here)
        self.listen(5)
        self.eqLoc = 0
        self.dcLoc = 0
        self.calib = 0

    def handle_accept(self):
        proxy_receiver(self, self.accept())

class proxy_receiver(asynchat.async_chat):
    channel_counter = 0

    def __init__(self, server, args):
        (conn, addr) = args
        asynchat.async_chat.__init__(self, conn)
        self.set_terminator('\n')
        self.server = server
        self.id = self.channel_counter
        self.channel_counter = self.channel_counter + 1
        self.buffer = ''

    def collect_incoming_data(self, data):
        self.buffer = self.buffer + data

    def found_terminator(self):
        data = self.buffer
        self.buffer = ''
        print('Process: ' + data)
        self.process_data(data)

    def process_data(self, data):
        cmd = data.split(' ')
        res =''
        if cmd[1] == 'm':
            res = 'move:EXECUTE,' + cmd[2] + ',' + cmd[3] + ',' + cmd[4] + '\n'
            if int(cmd[4]) > 200:
                clicks = 200
                status = 2
            else:
                clicks = int(cmd[4])
                status = 0
            if cmd[2] == 'E':
                if int(cmd[3]) == 0:
                    self.server.eqLoc += clicks
                else:
                    self.server.eqLoc -= clicks
            else:
                if int(cmd[3]) == 0:
                    self.server.dcLoc -= clicks
                else:
                    self.server.dcLoc += clicks
            res += ('location:(' + str(self.server.eqLoc) + ','
                    + str(self.server.dcLoc)+ '),' + str(self.server.calib) + '\n')
            res += ('move:COMPLETE,'+ str(status) + ',' + cmd[2] + ',' + cmd[3] + ','
                    + cmd[4] + '\n')
        elif cmd[1] == 'l':
            res = "limits:0,0,1,0,0,1\n"
        elif cmd[1] == 'r':
            res = ('location:(' + str(self.server.eqLoc) + ','
                   + str(self.server.dcLoc) + '),'
                   + str(self.server.calib) + '\n')
        elif cmd[1] =='e':
            self.server.eqLoc = int(cmd[2])
            self.server.dcLoc = int(cmd[3])
            self.server.calib = int(cmd[4])
        print('Respond: ' + res)
        self.push(res)

    def handle_close(self):
        print('Closing')
        self.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: %s <server-host> <server-port>' % sys.argv[0])
    else:
        ps = proxy_server(sys.argv[1], int(sys.argv[2]))
        asyncore.loop()
