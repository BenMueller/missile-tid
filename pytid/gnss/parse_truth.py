"""
CODE publishes coarse ionosphere data
ftp://igs.ensg.ign.fr/pub/igs/products/ionosphere/2020/
this is to help parse it to compare to our own data
"""

from datetime import datetime, timedelta
import numpy
import re

from laika.lib import coordinates

fname = "/home/tyler/projects/acw/tec_ground_truth_2020_feb_17.20i"


def read_ionomap(f):
    # map of lat->lon->tec
    ion = dict()
    assert f.readline().strip().endswith("START OF TEC MAP")
    dateline = f.readline().strip()
    assert dateline.endswith("EPOCH OF CURRENT MAP")

    date_arg = [int(x) for x in dateline.split()[:6]]
    # whatever this confuses datetime
    if date_arg[3] == 24:
        return None
    date = datetime(*date_arg)


    while True:
        header = f.readline().strip()
        if header.endswith("END OF TEC MAP"):
            return date, ion

        assert header.endswith("LAT/LON1/LON2/DLON/H")
        match = re.match("\s*(-?\d+\.\d+)" * 5 + ".*", header)
        lat, lon1, lon2, dlon, h = [float(x) for x in match.groups()]

        tecs = []
        lines_to_read = int((((lon2-lon1)/dlon + 1) + 15)//16)
        for j in range(lines_to_read):
            tecs += [float(x)/10 for x in f.readline().split()]

        ion[lat] = dict()
        for i, lon in enumerate(numpy.arange(lon1, lon2 + dlon, dlon)):
            ion[lat][lon] = tecs[i]

    return date, ion

def conv_ionmap(ion):
    convion = dict()

    dates = list(ion.keys())
    lats = list(ion[dates[0]].keys())
    lons = list(ion[dates[0]][lats[0]].keys())

    for lat in lats:
        convion[lat] = dict()
        for lon in lons:
            convion[lat][lon] = dict()
            for date in dates:
                convion[lat][lon][date] = ion[date][lat][lon]

    return convion

def conv_tecs(tecs, startdate):
    convion = dict()
    for (lat, lon, tick), tec in tecs.items():
        if lat not in convion:
            convion[lat] = dict()
        if lon not in convion[lat]:
            convion[lat][lon] = dict()
        convion[lat][lon][startdate + timedelta(seconds=tick*30)] = tec
    return convion

def compare(tecs, convdmap, startdate):
    for (lat, lon, tick) in tecs.keys():
        time = startdate + timedelta(seconds=tick*30)
        if time in convdmap[lat][lon]:
            print((lat, lon, tick), convdmap[lat][lon][time], tecs[(lat, lon, tick)])

def parse_ionmap(fname):
    f = open(fname)
    ion = dict()
    while True:
        line = f.readline().strip()
        if line.endswith("# OF MAPS IN FILE"):
            ticks = int(line.split()[0])
        elif line.endswith("END OF HEADER"):
            break

    for _ in range(ticks):
        res = read_ionomap(f)
        if res is None:
            continue
        date, iondat = res
        ion[date] = iondat

    return ion

def est_tec(ionmap, startdate, tick, pos):
    # round time to 15 minutes
    time = tick * 30
    rounded_minutes = round(time / (15 * 60)) * (15)
    obs_time = startdate + timedelta(minutes=rounded_minutes)

    lat, lon, _ = coordinates.ecef2geodetic(pos)
    rlat = round(lat / 2.5) * 2.5
    rlon = round(lon / 5) * 5

    return ionmap[obs_time][rlat][rlon]