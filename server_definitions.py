import json
import math
"""
Every JSON Command Object will have:
    "name" = "purcell"
    "cmd" = PurcellCommand.???

    for "cmd" = MOVE
        "unit" = sky_point.???
        "locA" = EQ or AZ location (A, B, C)
        "locB" = DC or EL location (A, B, C)
            ^^These are final locations not relative locations

    for "cmd" = RADIO
        I Don't know yet

    for "cmd" = INFO
        "info" = InfoCommand.???
        if "info" = LOC
            "unit" = sky_point.???
        if "info" = SET_LOCATION
            "unit"
            "locA"
            "locB"

Every JSON Response Object will have:
    "name" = "purcell"
    "res" = PurcellResponse.???

    for "res" = CONNECT
        if you can connect
            "connect" = True
        otherwise
            "connect" = False

    for "res" = MOVE
        "unit" = sky_point.???
        "status" = MoveStatus.???
        "locA" = EQ or AZ location (A, B, C)
        "locB" = DC or EL location (A, B, C)


    for "res" = RADIO
        "data" = ???
        ?????

    for "res" = INFO
        "info" = "InfoCommand"
        if "info" = LIMITS
            limits = (Eq A, Eq B, Eq Lk, Dc A, Dc B, Dc Lk)
        if "info" = LOC
             "unit" = sky_point.???
            "locA" = EQ or AZ location (A, B, C)
            "locB" = DC or EL location (A, B, C)
"""


class PurcellCommand(object):
    CONNECT, MOVE, RADIO, INFO = range(4)
    def __init__(self, type, data=None):
        self.type = type
        self.data = data

class PurcellResponse(object):
    CONNECT, MOVE, RADIO, INFO, FAIL = range(4,9)
    def __init__(self, type, data=None):
        self.type = type
        self.data = data


class MoveStatus(object):
    #This order is required so things line up with the Arduino response
    SUCCESS, LIMIT, TIMEOUT, ERROR, EXECUTE = range(5)
    def __init__(self):
        pass

class Info(object):
    LIMITS, LOC, SET_LOCATION, TELESCOPE = range(4)
    def __init__(self):
        pass

def FailResponse(message):
    return json.dumps({"name": "purcell",
                       "res": PurcellResponse.FAIL,
                       "message": message})

def ConnectResponse():
    return json.dumps({"name": "purcell",
                       "res": PurcellResponse.CONNECT})

def LocationResponse(unit, locs):
    (locA, locB) = locs
    return json.dumps({"name": "purcell",
                       "res": PurcellResponse.INFO,
                       "info": Info.LOC,
                       "unit": unit,
                       "locA": locA,
                       "locB": locB})

def LimitResponse(limits):
    return json.dumps({"name": "purcell",
                       "res": PurcellResponse.INFO,
                       "info": Info.LIMITS,
                       "limits": limits})

def MoveResponse(exit_status, unit=None, locA=None, locB=None):
    return json.dumps({"name": "purcell",
                       "res": PurcellResponse.MOVE,
                       "status": exit_status,
                       "unit": unit,
                       "locA": locA,
                       "locB": locB})
