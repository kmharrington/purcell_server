import asynchat
import asyncore
import socket
import json
import server_definitions as s
from sky import *

class proxy_server(asyncore.dispatcher):
    """
    The server is created off a proxy server template,
    since it's functionality is basically that.
    The proxy_server functions as the server part of the connection
    with the communication funneled through the proxy_receiver. The client
    part of the connection is done through the proxy_sender
    Telescope Arduino 192.168.1.12 port 1420 <<----proxy_sender
    proxy_receiver 'localhost' port 9420 <<---- Whatever client we need
    """
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.tel = telescope()
        self.there = (host, port)
        here = ('', port + 8000)
        self.bind(here)
        self.clientAddr = None
        self.hasClient = False
        self.listen(5)
        self.sender = proxy_sender(self, self.there)

    def handle_accept(self):
        if not self.hasClient:
            proxy_receiver(self, self.sender, self.accept())
        else:
            self.reject_client(self.accept())

    def handle_close(self):
        self.close()

    def reject_client(self, (conn, addr)):
        '''
        The Arduino should only have one client at a time,
        all other attempts to connect are rejected
        '''
        print('Rejecting Client')
        data = conn.recv(8192)
        if data.rfind('RUBUSY') != -1:
            conn.sendall('YES Client at: ' + str(addr))
        else:
            conn.sendall('Fail')
        conn.close()

class proxy_sender(asynchat.async_chat):
    '''
    proxy_sender contains the connection with the Arduino
    proxy_sender.push("thing") sends the message to the Arduino
    '''
    def __init__(self, server, address):
        asynchat.async_chat.__init__(self)
        self.server = server
        self.receiver = None
        self.set_terminator(None)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.buffer = ''
        self.set_terminator('\n')
        self.connect(address)
        self.id = 0

    def handle_connect(self):
        """
        I'd like for the first things sent to the telescope to
        be requests for location and limit status but that's not
        working yet
        """
        print('Sender Connected')
        self.server.tel.requestLocation(self)
        self.server.tel.requestLimits(self)

    def collect_incoming_data(self, data):
        self.buffer = self.buffer + data

    def found_terminator(self):
        data = self.buffer
        self.buffer = ''
        print('==> (%d) %s' % (self.id, repr(data)))
        self.process_response(data)

    def process_response(self, data):
        """
        Called to process a line of data sent by the Arduino.
        Options:
         move:EXECUTE,E/D,0/1,### <--Encoder Clicks
         move:COMPLETE,status,E/D,0/1,###
         location:(Eq,Dc)
         limits:0,0,1,0,0,1
         error:message
        Updates Telescope Objects and sends response to receiver
        """
        data = data.split(":")
        if data[0] == 'move':
            cmd = data[1].split(',')
            if cmd[0] == 'EXECUTE':
                if self.server.tel.currentMoveGoal == None:
                    print('This is a problem')
                (ha, dc) = self.server.tel.clicks2hadc(
                    self.server.tel.currentMoveGoal)
                self.receiver.push(s.MoveResponse(s.MoveStatus.EXECUTE,
                                                  sky_point.HADC, ha, dc) + '\n')
            elif cmd[0] == 'COMPLETE':
                status = int(cmd[1])
                #If we hit a limit switch, find out which one
                if status == s.MoveStatus.LIMIT:
                    self.server.tel.requestLimits(self)
                    motor = cmd[2]
                    if motor == 'E':
                        self.server.tel.setLocGoal((self.server.tel.getLocation()[0], self.server.tel.getLocGoal()[1]))
                    else:
                        self.server.tel.setLocGoal((self.server.tel.getLocGoal()[0], self.server.tel.getLocation()[1]))
                self.server.tel.currentMoveGoal = None
                (ha, dc) = self.server.tel.clicks2hadc(
                    self.server.tel.getLocation())
                self.receiver.push(s.MoveResponse(status, sky_point.HADC,
                                                  ha, dc) + '\n')
                self.server.tel.updateStatus(self)
        elif data[0] == 'location':
            cmd = data[1].split(',')
            eq = int(cmd[0][1:])
            dc = int(cmd[1][:-1])
            self.server.tel.setLocation(eq, dc)
        elif data[0] == 'limits':
            limits = data[1].split(',')
            for i in range(len(limits)):
                self.server.tel.setLimitStatus(i, int(limits[i]))
            if self.receiver:
                self.receiver.push(s.LimitResponse(
                    self.server.tel.getLimitStatus()) + '\n')
        elif data[0] == 'error':
            self.receiver.push(s.FailResponse("Motor Error: " + data[1]) + '\n')

    def handle_close(self):
        if self.receiver:
            self.receiver.close()
        self.close()

class proxy_receiver(asynchat.async_chat):
    '''
    proxy_receiver contains the connection with the client.
    proxy_receiver.push("thing) sends a message to the client
    Most of these responses are in the server_definitions response
    forms so that all the required fields exist
    '''
    channel_counter = 0
    def __init__(self, server, sender, args):
        (conn, addr) = args
        asynchat.async_chat.__init__(self, conn)
        self.set_terminator('\n')
        self.server = server
        self.server.clientAdd = addr
        self.id = self.channel_counter
        self.channel_counter = self.channel_counter + 1
        self.sender = sender
        self.sender.receiver = self
        self.sender.id = self.id
        self.buffer = ''

    def handle_connect(self):
        print('Reciever connected')
        self.server.hasClient = True

    def collect_incoming_data(self, data):
        self.buffer = self.buffer + data

    def found_terminator(self):
        data = self.buffer
        self.buffer = ''
        print('<== (%d) %s' % (self.id, repr(data)))
        self.process_request(data)
        # self.sender.push(data + '\n')

    def handle_close(self):
        print('Closing')
        self.server.hasClient = False
        self.server.clientAdd = None
        #self.sender.close()
        self.close()

    def process_request(self, data):
        """
        Processes commands from the client.
        'RUBUSY' is the initial ping used to determine if the client can connect
        Each command has a required set of keys listed in server_definitions.py
        """
        if data.rfind('RUBUSY') != -1:
            self.push(s.ConnectResponse()+'\n')
        else:
            try:
                commands = json.loads(data)
            except ValueError as e:
                self.push(s.FailResponse("Response not in JSON format") + '\n')
                return
            for cmd in commands:
                try:
                    if cmd['cmd'] == s.PurcellCommand.CONNECT:
                        self.push(s.ConnectResponse() + '\n')
                    elif cmd['cmd'] == s.PurcellCommand.MOVE:
                        print 'Move Command'
                        self.moveCommand(cmd)
                    elif cmd['cmd'] == s.PurcellCommand.RADIO:
                        print 'Radio Command'
                    elif cmd['cmd'] == s.PurcellCommand.INFO:
                        print 'Info Command'
                        self.infoCommand(cmd)
                    else:
                        self.push(s.FailResponse("cmd option not known") + '\n')
                except KeyError as e:
                    self.push(s.FailResponse("no cmd key") + '\n')
                    continue

    def moveCommand(self, cmd):
        """
        Processes move command. Updates the telescope's goal location
        and if the telescope is IDLE then it tells the telescope to move.
        Otherwise just the goal location will be updated. The current construction
        ensures only one move command is sent to the Arduino at a time.

        After every move:COMPLETE returns from the Arduino, telescope.updateStatus
        will run and move the telescope if the goal location is not the current
        location
        """
        try:
            locA = cmd['locA']
            locB = cmd['locB']
            unit = cmd['unit']
        except KeyError as e:
            self.push(s.FailResponse("Missing Required Key") + '\n')
            return
        pnt = sky_point(unit, locA, locB)
        new_ha, new_dec = pnt.getLoc(sky_point.HADC)
        self.server.tel.setLocGoal(self.server.tel.hadc2clicks((new_ha,
                                                                new_dec)))
        if not self.server.tel.willMoveOnUpdate():
            self.push(s.FailResponse("Distance to move is too small") + '\n')
        # if telescope is moving then do nothing
        if self.server.tel.isIdle():
            self.server.tel.updateStatus(self.sender)

    def infoCommand(self, cmd):
        try:
            info = cmd['info']
            if info == s.Info.LOC:
                unit = cmd['unit']
            elif info == s.Info.SET_LOCATION:
                unit = cmd['unit']
                locA = cmd['locA']
                locB = cmd['locB']
        except KeyError as e:
            self.push(s.FailResponse("Missing Required Key") +'\n')
            return
        if info == s.Info.LIMITS:
            self.server.tel.requestLimits(self.sender)
        elif info == s.Info.LOC:
            '''
            The Telescope Class will always know the location because every
            Move Command will get a location update from the Arduino which is
            immediately updated in the telescope class.
            '''
            (ha, dc) = self.server.tel.clicks2hadc(self.server.tel.getLocation())
            pnt = sky_point(sky_point.HADC, ha, dc)
            self.push(s.LocationResponse(unit, pnt.getLoc(unit)) + '\n')
        elif info == s.Info.SET_LOCATION:
            pnt = sky_point(unit, locA, locB)
            self.server.tel.setTelescopeLocation(
                self.server.tel.hadc2clicks(pnt.getLoc(sky_point.HADC)),
                self.sender)

class telescope:
    """
    This class stores properties and methods which relate to the actual
    hardware of the telescope. It's used to translate between encoder clicks
    and sky position, contains the current location and limit status. It also
    creates the move commands to send to the Arduino so that only one command
    is issued at a time.

    Contains
        (eq_clicks, dc_clicks) -- The current location of the telescope,
                                  not updated until a move has been completed
        (eq_goal, dc_goal)     -- The most recent location the client sent
                                  a request to move to
        status - MOVING or IDLE. Telescope is only idle if it is
                 which a minimum step of the goal location
        currentMoveGoal - Thing used to tell the client where the current move
                          should leave the telescope
    """

    IDLE, MOVING = range(2)
    CLKS_PER_DEG = 11.1
    # minimum step telescope can do, currently: 5 clks * deg/clk
    MIN_STEP = (0, 27, 0)
    MIN_STEP_CLICKS = 5

    def __init__(self):
        self.status = telescope.IDLE
        # _clicks and _goal are in absolute encoder clicks
        self.eq_clicks = 0
        self.dc_clicks = 0
        self.eq_goal = 0
        self.dc_goal = 0
        self.currentMoveLoc = None
        self.limitStatus = [0, 0, 0, 0, 0, 0]

    def isIdle(self):
        '''Because isIdle() is shorter to write'''
        if self.status == telescope.IDLE:
            return True
        else:
            return False

    def setLocGoal(self, newargs):
        (newEq, newDC) = newargs
        self.eq_goal = newEq
        self.dc_goal = newDC
        print 'Current Goals: ', (self.eq_goal, self.dc_goal)

    def getLocGoal(self):
        return (self.eq_goal, self.dc_goal)

    def setLocation(self, newEq, newDC):
        self.eq_clicks = newEq
        self.dc_clicks = newDC
        print('New Location: ', (self.eq_clicks, self.dc_clicks))

    def getLocation(self):
        return (self.eq_clicks, self.dc_clicks)

    def setTelescopeLocation(self, Clicks, sender):
        (eqClicks, dcClicks) = Clicks
        command = 'cmd e ' + str(eqClicks) + ' ' + str(dcClicks) + '\ncmd r\n'
        sender.push(command)
        self.setLocGoal(eqClicks, dcClicks)

    def willMoveOnUpdate(self):
        if (abs(self.eq_goal - self.eq_clicks) > telescope.MIN_STEP_CLICKS or
            abs(self.dc_goal - self.dc_clicks) > telescope.MIN_STEP_CLICKS):
            return True
        return False

    def moveEQ(self, sender):
        if abs(self.eq_goal - self.eq_clicks) > telescope.MIN_STEP_CLICKS:
            toMove = self.eq_goal - self.eq_clicks
            self.currentMoveGoal = (self.eq_goal, self.dc_clicks)
            command = 'cmd m E '
            if toMove < 0:
                command += '1 '
            else:
                command += '0 '
            command += str(abs(toMove))
            sender.push(command + '\n')
            return False
        else:
            self.eq_goal = self.eq_clicks
            return True

    def moveDC(self, sender):
        if abs(self.dc_goal - self.dc_clicks) > telescope.MIN_STEP_CLICKS:
            toMove = self.dc_goal - self.dc_clicks
            self.currentMoveGoal = (self.eq_clicks, self.dc_goal)
            command = 'cmd m D '
            if toMove < 0:
                command += '0 '
            else:
                command += '1 '
            command += str(abs(toMove))
            sender.push(command + '\n')
            return False
        else:
            self.dc_goal = self.dc_clicks
            return True

    def requestLocation(self, sender):
        sender.push('cmd r\n')
    def requestLimits(self, sender):
        sender.push('cmd l\n')
    def setLimitStatus(self, index, status):
        self.limitStatus[index] = status
    def getLimitStatus(self):
        return self.limitStatus

    def hadc2clicks(self, args):
        (ha, dec) = args
        ha_clicks = telescope.CLKS_PER_DEG * (ha[0] + ha[1] / 60.0
                                              + ha[2] / 3600.0)
        dec_clicks = telescope.CLKS_PER_DEG * (dec[0] + dec[1] / 60.0
                                               + dec[2] / 3600.0)
        return (int(ha_clicks), int(dec_clicks))

    def clicks2hadc(self, clicks):
        (ha_clicks, dec_clicks) = clicks
        ha_deg = ha_clicks / telescope.CLKS_PER_DEG
        dec_deg = dec_clicks / telescope.CLKS_PER_DEG
        return (degrees2tuple(ha_deg), degrees2tuple(dec_deg))

    # Only call updateStatus when you're willing to send a move
    # command to the telescope
    def updateStatus(self, sender):
        # We only move Eq OR Dc b/c we don't want to pile up commands
        # on the Arduino

        #returns true if we don't have to move Eq
        if self.moveEQ(sender):
            #returns true if we don't have to move DC
            if self.moveDC(sender):
                self.status = telescope.IDLE
            else:
                self.status = telescope.MOVING
        else:
            self.status = telescope.MOVING


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: %s <server-host> <server-port>' % sys.argv[0])
    else:
        ps = proxy_server(sys.argv[1], int(sys.argv[2]))
        asyncore.loop()
