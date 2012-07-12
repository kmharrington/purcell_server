import asyncore, socket
import json
import sky
import server_definitions as s

class HTTPClient(asyncore.dispatcher):

    def __init__(self, host, port, path):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (host, port) )
        data = [#{'name':'purcell','cmd':s.PurcellCommand.INFO,'info':s.Info.LOC, 'unit':sky.sky_point.HADC}]
                {'name':'purcell','cmd':s.PurcellCommand.MOVE,'unit':sky.sky_point.HADC,'locA':(85,0,0),'locB':(41,0,0)}]#,
                #{'name':'purcell','cmd':s.PurcellCommand.MOVE,'unit':sky.sky_point.HADC,'locA':(15,0,0),'locB':(20,0,0)},
                
                #{'name':'purcell','cmd':s.PurcellCommand.INFO,'info':s.Info.LIMITS},
                #{'name':'purcell','cmd':s.PurcellCommand.INFO, 'info':s.Info.SET_LOCATION, 'unit':sky.sky_point.HADC, 'locA':(0,0,0), 'locB':(0,0,0)}]

        self.buffer = 'RUBUSY\n'+ json.dumps(data)+'\n'
        #self.buffer = 'RUBUSY\n RAWERRRERE\n'

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        print self.recv(8192)

    def writable(self):
        return (len(self.buffer) > 0)

    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]


if __name__ == '__main__':
    import sys
    import string
    if len(sys.argv) < 3:
        print 'Usage: %s <server-host> <server-port>' % sys.argv[0]
    else:
        client = HTTPClient(sys.argv[1], string.atoi (sys.argv[2]), '/')
        asyncore.loop()
