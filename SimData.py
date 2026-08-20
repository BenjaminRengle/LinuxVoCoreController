"""Generalized data structures for sim data, car data, and proximity data
from different sims (rFactor2 e.g.).

These are the app's own internal representation, built in Python from
whatever the sim-specific reader (e.g. RFactor2Data.py) parses out of raw
shared memory. They aren't read directly from raw bytes themselves, so
there's no need for ctypes' fixed C memory layout here - plain dataclasses
give real defaults (no implicit zero-filled "phantom" fields), native str
instead of fixed-size char buffers, and variable-length lists instead of
oversized fixed arrays.
"""
from dataclasses import dataclass, field

MAXCARS = 128
PROXCARS = 6


@dataclass
class LapTime:
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    fraction: int = 0


@dataclass
class LapData:
    delta: float = 0.0
    startTime: int = 0
    lapTime: LapTime = field(default_factory=LapTime)


@dataclass
class CarData:
    xpos: float = 0.0
    ypos: float = 0.0
    zpos: float = 0.0
    carspline: float = 0.0
    speed: float = 0.0
    pos: int = 0
    lap: int = 0
    trackpos: int = 0
    place: int = 0
    timebehindleader: float = 0.0
    lastlap: LapTime = field(default_factory=LapTime)
    bestlap: LapTime = field(default_factory=LapTime)
    inpit: bool = False
    inpitlane: bool = False
    ingarage: bool = False
    inpitentrance: bool = False
    inpitexit: bool = False
    inpitstopped: bool = False
    driver: str = ""
    car: str = ""


@dataclass
class ProximityData:
    radius: float = 0.0
    theta: float = 0.0
    lap: int = 0


def _zeros4():
    return [0.0, 0.0, 0.0, 0.0]


def _proximity_cars():
    return [ProximityData() for _ in range(PROXCARS)]


@dataclass
class SimData:
    mtick: int = 0
    prev_mtick: int = 0

    simstatus: int = 0
    velocity: int = 0
    rpms: int = 0
    gear: int = 0
    pulses: int = 0
    maxrpm: int = 0
    idlerpm: int = 0
    maxgears: int = 0
    altitude: int = 0
    lap: int = 0
    position: int = 0
    numlaps: int = 0
    playerlaps: int = 0
    numcars: int = 0
    gearc: str = ""

    Xvelocity: float = 0.0
    Yvelocity: float = 0.0
    Zvelocity: float = 0.0

    worldXvelocity: float = 0.0
    worldYvelocity: float = 0.0
    worldZvelocity: float = 0.0

    gas: float = 0.0
    brake: float = 0.0
    fuel: float = 0.0
    fuelcapacity: float = 0.0
    clutch: float = 0.0
    steer: float = 0.0
    handbrake: float = 0.0

    turboboost: float = 0.0
    turboboostperct: float = 0.0
    maxturbo: float = 0.0

    abs: float = 0.0
    brakebias: float = 0.0
    tyreRPS: list = field(default_factory=_zeros4)
    tyrediameter: list = field(default_factory=_zeros4)
    tyreslipratio: list = field(default_factory=_zeros4)
    tyreslipangle: list = field(default_factory=_zeros4)
    distance: float = 0.0

    heading: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    worldposx: float = 0.0
    worldposy: float = 0.0
    worldposz: float = 0.0

    braketemp: list = field(default_factory=_zeros4)
    tyrewear: list = field(default_factory=_zeros4)
    tyretemp: list = field(default_factory=_zeros4)
    tyrepressure: list = field(default_factory=_zeros4)

    tyrecontact0: list = field(default_factory=_zeros4)
    tyrecontact1: list = field(default_factory=_zeros4)
    tyrecontact2: list = field(default_factory=_zeros4)

    airdensity: float = 0.0
    airtemp: float = 0.0
    tracktemp: float = 0.0

    suspension: list = field(default_factory=_zeros4)
    suspvelocity: list = field(default_factory=_zeros4)

    trackdistancearound: float = 0.0
    playerspline: float = 0.0
    trackspline: float = 0.0
    playertrackpos: int = 0
    tracksamples: int = 0

    lastlap: LapTime = field(default_factory=LapTime)
    bestlap: LapTime = field(default_factory=LapTime)
    currentlap: LapTime = field(default_factory=LapTime)
    currentlapinseconds: int = 0
    lastlapinseconds: int = 0
    time: int = 0
    sessiontime: LapTime = field(default_factory=LapTime)
    session: int = 0
    sectorindex: int = 0
    sector1time: float = 0.0
    sector2time: float = 0.0
    lastsectorinms: int = 0
    gamephase: int = 0
    currentet: float = 0.0
    endet: float = 0.0
    playerflag: int = 0
    playercardata: CarData = field(default_factory=CarData)
    lapisvalid: bool = False
    cars: list = field(default_factory=list)
    pd: list = field(default_factory=_proximity_cars)

    car: str = ""
    track: str = ""
    driver: str = ""
    tyrecompound: str = ""

    simapi: int = 0
    simexe: int = 0
    simon: bool = False
    simapiversion: int = 0
