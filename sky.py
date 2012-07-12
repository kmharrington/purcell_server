import ephem as ep
# See http://rhodesmill.org/pyephem/radec for why I'm using this library.
# It basically corrects for everything ever.

'''
locA and locB are (A,B,C) tuples
'''

class sky_point:
    RADC, GALACTIC, AZEL, HADC = range(4)
    TELESCOPE_LATITUDE = ep.degrees("42:21:38.67")
    TELESCOPE_LONGITUDE = ep.degrees("-71:05:27.84")

    def __init__(self, unit, locA, locB):
        if len(locA) != 3 or len(locB) != 3:
            print("Bad Locations given")
            return
        self.telescope = ep.Observer()
        self.telescope.lat = self.TELESCOPE_LATITUDE
        self.telescope.lon = self.TELESCOPE_LONGITUDE
        # Neglect the atmosphere b/c we're using radio waves
        self.telescope.pressure = 0
        # Approximate Elevation
        self.telescope.elevation = 30
        self.location = None
        if unit == sky_point.RADC:
            line = ('thing,f,' + self.loc2str(locA) + ','
                    + self.loc2str(locB) + ',1')
            self.location = ep.readdb(line)
        elif unit == sky_point.GALACTIC:
            ga = ep.Galactic(self.loc2str(locA), self.loc2str(locB),
                             epoch=ep.J2000)
            eq = ep.Equatorial(ga)
            line = 'thing,f,' + str(eq.ra) + ',' + str(eq.dec) + ',1'
            self.location = ep.readdb(line)
        elif unit == sky_point.AZEL:
            ra,dec = self.telescope.radec_of(self.loc2str(locA),
                                             self.loc2str(locB))
            line = 'thing,f,' + str(ra) + ',' + str(dec) + ',1'
            self.location = ep.readdb(line)
        elif unit == sky_point.HADC:
            ra = ep.hours(self.telescope.sidereal_time()
                          - ep.degrees(self.loc2str(locA)))
            line = 'thing,f,' + str(ra) + ',' + self.loc2str(locB) + ',1'
            self.location = ep.readdb(line)
        else:
            print('Error, Unknown Units')
            return
        self.location.compute(self.telescope)

    def loc2str(self, loc):
       return str(loc[0]) + ':' + str(loc[1]) + ':' + str(loc[2])

    def getLoc(self, unit = RADC):
        self.location.compute(self.telescope)
        if unit == sky_point.RADC:
            return (angle2tuple(self.location.ra),
                    angle2tuple(self.location.dec))
        elif unit == sky_point.GALACTIC:
            ga = ep.Galactic(self.location)
            return (angle2tuple(ga.lon), angle2tuple(ga.lat))
        elif unit == sky_point.AZEL:
            return (angle2tuple(self.location.az),
                    angle2tuple(self.location.alt))
        elif unit == sky_point.HADC:
            ha = ep.degrees(self.telescope.sidereal_time() - self.location.ra)
            return (angle2tuple(ha), angle2tuple(self.location.dec))

    def __str__(self):
        self.location.compute(self.telescope)
        return ('Location At RA:' + str(self.location.ra) +
                ' , DEC:' + str(self.location.dec) +
                '\nAZ: ' + str(self.location.az) +
                ' , EL: ' + str(self.location.alt))

def degrees2tuple(deg):
    ang = ep.degrees(str(deg))
    return angle2tuple(ang)

def angle2tuple(angle):
    if type(angle) != ep.Angle:
        print('fail')
        return
    x = str(angle).split(':')
    return (int(x[0]), int(x[1]), int(float(x[2])))

if __name__ == '__main__':
    thing1 = sky_point(sky_point.HADC, (0, 0, 0), (0, 0, 0))
    thing2 = sky_point(sky_point.AZEL, (13, 23, 54), (23, 54, 23))
    thing3 = sky_point(sky_point.GALACTIC, (13, 23, 54), (23, 54, 23))
    print('Thing 1: ' + str(thing1))
    print('Galactic: ' + str(thing1.getLoc(sky_point.GALACTIC)))
    print('Hour Angle: ' + str(thing1.getLoc(sky_point.HADC)))
    print('Sidereal Time: ' + str(thing1.telescope.sidereal_time()))
    # print('Thing 2: \n', thing2.getHADC(),'\n'+str(thing2))
    # print('Thing 3: \n', thing3.getHADC(),'\n'+str(thing3))
