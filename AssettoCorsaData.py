import ctypes
from SimData import *
import os
import mmap

AC_PHYSICS_PATH = "acpmf_physics"#"/dev/shm/acpmf_physics"
AC_STATIC_PATH = "acpmf_static"#"/dev/shm/acpmf_static"
AC_GRAPHIC_PATH = "acpmf_graphics"#"/dev/shm/acpmf_graphics"


def ac_convert_to_simdata_laptime(ac_laptime_ms):
    if ac_laptime_ms <= 0:
        return LapTime(hours=0, minutes=0, seconds=0, fraction=0)

    total_seconds = ac_laptime_ms / 1000.0
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    fraction = int(ac_laptime_ms - (hours * 3600000) - (minutes * 60000) - (seconds * 1000))
    if fraction < 0:
        fraction = 0
    if fraction > 999:
        fraction = 999
    return LapTime(hours=hours, minutes=minutes, seconds=seconds, fraction=fraction)


def spline_length_to_distance_around_track(track_length, spline):
    """spline is AC's 0..1 normalized track position - convert to meters."""
    if spline < 0.0:
        spline -= 1
    return spline * track_length


class ACStatus:
    """AC_STATUS values, as observed for sim_data.gamephase.

    AC has no rF2-style race-control flag state machine - this is the
    closest equivalent (off/replay/live/paused), and its meaning is AC-
    specific just like GamePhase's meaning (in RFactor2Data.py) is rF2-
    specific. sim_data.gamephase's raw value is not comparable across sims.
    """

    OFF = 0
    REPLAY = 1
    LIVE = 2
    PAUSE = 3


class ACSessionType:
    """AC_SESSION_TYPE values, as observed for sim_data.session.

    Like ACStatus vs. GamePhase, this uses a completely different value
    scale than rFactor2's Session class (RFactor2Data.py) - sim_data.session
    is only meaningful relative to whichever sim produced it.
    """

    UNKNOWN = -1
    PRACTICE = 0
    QUALIFY = 1
    RACE = 2
    HOTLAP = 3
    TIME_ATTACK = 4
    DRIFT = 5
    DRAG = 6


class ACVec3(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
    ]
    _pack_ = 4


class SPageFilePhysics(ctypes.Structure):
    _fields_ = [
        ("packetId", ctypes.c_int),
        ("gas", ctypes.c_float),
        ("brake", ctypes.c_float),
        ("fuel", ctypes.c_float),
        ("gear", ctypes.c_int),
        ("rpms", ctypes.c_int),
        ("steerAngle", ctypes.c_float),
        ("speedKmh", ctypes.c_float),
        ("velocity", ctypes.c_float * 3),
        ("accG", ctypes.c_float * 3),
        ("wheelSlip", ctypes.c_float * 4),
        ("wheelLoad", ctypes.c_float * 4),
        ("wheelsPressure", ctypes.c_float * 4),
        ("wheelAngularSpeed", ctypes.c_float * 4),
        ("tyreWear", ctypes.c_float * 4),
        ("tyreDirtyLevel", ctypes.c_float * 4),
        ("tyreCoreTemperature", ctypes.c_float * 4),
        ("camberRAD", ctypes.c_float * 4),
        ("suspensionTravel", ctypes.c_float * 4),
        ("drs", ctypes.c_float),
        ("tc", ctypes.c_float),
        ("heading", ctypes.c_float),
        ("pitch", ctypes.c_float),
        ("roll", ctypes.c_float),
        ("cgHeight", ctypes.c_float),
        ("carDamage", ctypes.c_float * 5),
        ("numberOfTyresOut", ctypes.c_int),
        ("pitLimiterOn", ctypes.c_int),
        ("abs", ctypes.c_float),
        ("kersCharge", ctypes.c_float),
        ("kersInput", ctypes.c_float),
        ("autoShifterOn", ctypes.c_int),
        ("rideHeight", ctypes.c_float * 2),
        ("turboBoost", ctypes.c_float),
        ("ballast", ctypes.c_float),
        ("airDensity", ctypes.c_float),
        ("airTemp", ctypes.c_float),
        ("roadTemp", ctypes.c_float),
        ("localAngularVel", ctypes.c_float * 3),
        ("finalFF", ctypes.c_float),
        ("performanceMeter", ctypes.c_float),
        ("engineBrake", ctypes.c_int),
        ("ersRecoveryLevel", ctypes.c_int),
        ("ersPowerLevel", ctypes.c_int),
        ("ersHeatCharging", ctypes.c_int),
        ("ersIsCharging", ctypes.c_int),
        ("kersCurrentKJ", ctypes.c_float),
        ("drsAvailable", ctypes.c_int),
        ("drsEnabled", ctypes.c_int),
        ("brakeTemp", ctypes.c_float * 4),
        ("clutch", ctypes.c_float),
        ("tyreTempI", ctypes.c_float * 4),
        ("tyreTempM", ctypes.c_float * 4),
        ("tyreTempO", ctypes.c_float * 4),
        ("isAIControlled", ctypes.c_int),
        ("tyreContactPoint", ACVec3 * 4),
        ("tyreContactNormal", ACVec3 * 4),
        ("tyreContactHeading", ACVec3 * 4),
        ("brakeBias", ctypes.c_float),
        ("localVelocity", ACVec3),
        ("P2PActivation", ctypes.c_int),
        ("P2PStatus", ctypes.c_int),
        ("CurrentMaxRPM", ctypes.c_float),
        ("MZ", ctypes.c_float * 4),
        ("FX", ctypes.c_float * 4),
        ("FY", ctypes.c_float * 4),
        ("SlipRatio", ctypes.c_float * 4),
        ("SlipAngle", ctypes.c_float * 4),
        ("TCInAction", ctypes.c_int),
        ("ABSInAction", ctypes.c_int),
        ("SuspensionDamage", ctypes.c_float * 4),
        ("TyreTemp", ctypes.c_float * 4),
        ("WaterTemp", ctypes.c_float),
        ("BrakePressure", ctypes.c_float * 4),
        ("frontBrakeCompound", ctypes.c_int),
        ("rearBrakeCompound", ctypes.c_int),
        ("padLife", ctypes.c_float * 4),
        ("discLife", ctypes.c_float * 4),
        ("ignitionOn", ctypes.c_int),
        ("starterEngineOn", ctypes.c_int),
        ("isEngineRunning", ctypes.c_int),
        ("kerbVibration", ctypes.c_float),
        ("slipVibration", ctypes.c_float),
        ("gVibration", ctypes.c_float),
        ("absbVibration", ctypes.c_float),
    ]
    _pack_ = 4


class SPageFileGraphic(ctypes.Structure):
    _fields_ = [
        ("packetId", ctypes.c_int),
        ("status", ctypes.c_int),
        ("session", ctypes.c_int),
        ("currentTime", ctypes.c_uint16 * 15),
        ("lastTime", ctypes.c_uint16 * 15),
        ("bestTime", ctypes.c_uint16 * 15),
        ("split", ctypes.c_uint16 * 15),
        ("completedLaps", ctypes.c_int),
        ("position", ctypes.c_int),
        ("iCurrentTime", ctypes.c_int),
        ("iLastTime", ctypes.c_int),
        ("iBestTime", ctypes.c_int),
        ("sessionTimeLeft", ctypes.c_float),
        ("distanceTraveled", ctypes.c_float),
        ("isInPit", ctypes.c_int),
        ("currentSectorIndex", ctypes.c_int),
        ("lastSectorTime", ctypes.c_int),
        ("numberOfLaps", ctypes.c_int),
        ("tyreCompound", ctypes.c_uint16 * 33),
        ("replayTimeMultiplier", ctypes.c_float),
        ("normalizedCarPosition", ctypes.c_float),
        ("carCoordinates", ctypes.c_float * 3),
        ("PenaltyTime", ctypes.c_float),
        ("Flag", ctypes.c_int),
        ("Penalty", ctypes.c_int),
        ("IdealLineOn", ctypes.c_int),
        ("IsInPitLane", ctypes.c_int),
        ("SurfaceGrip", ctypes.c_float),
        ("MandatoryPitDone", ctypes.c_int),
        ("WindSpeed", ctypes.c_float),
        ("WindDirection", ctypes.c_float),
        ("IsSetupMenuVisible", ctypes.c_int),
        ("MainDisplayIndex", ctypes.c_int),
        ("SecondaryDisplayIndex", ctypes.c_int),
        ("TC", ctypes.c_int),
        ("TCUT", ctypes.c_int),
        ("EngineMap", ctypes.c_int),
        ("ABS", ctypes.c_int),
        ("FuelXLap", ctypes.c_float),
        ("RainLights", ctypes.c_int),
        ("FlashingLights", ctypes.c_int),
        ("LightsStage", ctypes.c_int),
        ("ExhaustTemperature", ctypes.c_float),
        ("WiperLV", ctypes.c_int),
        ("DriverStingTotalTimeLeft", ctypes.c_int),
        ("DriverStingTimeLeft", ctypes.c_int),
        ("RainTyres", ctypes.c_int),
        ("SessionIndex", ctypes.c_int),
        ("UsedFuel", ctypes.c_float),
        ("DeltaLapTime", ctypes.c_char * 15),
        ("IDeltaLapTime", ctypes.c_int),
        ("EstimatedLapTime", ctypes.c_char * 15),
        ("IEstimatedLapTime", ctypes.c_int),
        ("IsDeltaPositive", ctypes.c_int),
        ("ISplit", ctypes.c_int),
        ("IsValidLap", ctypes.c_int),
        ("FuelEstimatedLaps", ctypes.c_float),
        ("TrackStatus", ctypes.c_char * 33),
        ("MissingMandatoryPits", ctypes.c_int),
        ("directionLightsLeft", ctypes.c_int),
        ("directionLightsRight", ctypes.c_int),
        ("GlobalYellow", ctypes.c_int),
        ("GlobalYellow1", ctypes.c_int),
        ("GlobalYellow2", ctypes.c_int),
        ("GlobalYellow3", ctypes.c_int),
        ("GlobalWhite", ctypes.c_int),
        ("GlobalGreen", ctypes.c_int),
        ("GlobalChequered", ctypes.c_int),
        ("GlobalRed", ctypes.c_int),
        ("mfdTyreSet", ctypes.c_int),
        ("mfdFuelToAdd", ctypes.c_float),
        ("mfdTyrePressureLF", ctypes.c_float),
        ("mfdTyrePressureRF", ctypes.c_float),
        ("mfdTyrePressureLR", ctypes.c_float),
        ("mfdTyrePressureRR", ctypes.c_float),
        ("trackGripStatus", ctypes.c_int),
        ("rainIntensity", ctypes.c_int),
        ("rainIntensityIn10min", ctypes.c_int),
        ("rainIntensityIn30min", ctypes.c_int),
        ("currentTyreSet", ctypes.c_int),
        ("strategyTyreSet", ctypes.c_int),
        ("gapAhead", ctypes.c_int),
        ("gapBehind", ctypes.c_int),
    ]
    _pack_ = 4


class SPageFileStatic(ctypes.Structure):
    _fields_ = [
        ("smVersion", ctypes.c_uint16 * 15),
        ("acVersion", ctypes.c_uint16 * 15),
        ("numberOfSessions", ctypes.c_int),
        ("numCars", ctypes.c_int),
        ("carModel", ctypes.c_uint16 * 33),
        ("track", ctypes.c_uint16 * 33),
        ("playerName", ctypes.c_uint16 * 33),
        ("playerSurname", ctypes.c_uint16 * 33),
        ("playerNick", ctypes.c_uint16 * 33),
        ("sectorCount", ctypes.c_int),
        ("maxTorque", ctypes.c_float),
        ("maxPower", ctypes.c_float),
        ("maxRpm", ctypes.c_int),
        ("maxFuel", ctypes.c_float),
        ("suspensionMaxTravel", ctypes.c_float * 4),
        ("tyreRadius", ctypes.c_float * 4),
        ("MaxTurboBoost", ctypes.c_float),
        ("Deprecated1", ctypes.c_float),
        ("Deprecated2", ctypes.c_float),
        ("PenaltiesEnabled", ctypes.c_int),
        ("AidFuelRate", ctypes.c_float),
        ("AidTireRate", ctypes.c_float),
        ("AidMechanicalDamage", ctypes.c_float),
        ("AidAllowTyreBlankets", ctypes.c_int),
        ("AidStability", ctypes.c_float),
        ("AidAutoClutch", ctypes.c_int),
        ("AidAutoBlip", ctypes.c_int),
        ("HasDRS", ctypes.c_int),
        ("HasERS", ctypes.c_int),
        ("HasKERS", ctypes.c_int),
        ("KersMaxJoules", ctypes.c_float),
        ("EngineBrakeSettingsCount", ctypes.c_int),
        ("ErsPowerControllerCount", ctypes.c_int),
        ("TrackSPlineLength", ctypes.c_float),
        ("TrackConfiguration", ctypes.c_uint16 * 15),
        ("ErsMaxJ", ctypes.c_float),
        ("IsTimedRace", ctypes.c_int),
        ("HasExtraLap", ctypes.c_int),
        ("CarSkin", ctypes.c_uint16 * 33),
        ("ReversedGridPositions", ctypes.c_int),
        ("PitWindowStart", ctypes.c_int),
        ("PitWindowEnd", ctypes.c_int),
        ("IsOnline", ctypes.c_int),
        ("dryTyresName", ctypes.c_char * 33),
        ("wetTyresName", ctypes.c_char * 33),
    ]
    _pack_ = 4


class ACTelemetryReader:
    def __init__(self, physics_path=AC_PHYSICS_PATH, static_path=AC_STATIC_PATH, graphic_path=AC_GRAPHIC_PATH):
        self.physics_path = physics_path
        self.static_path = static_path
        self.graphic_path = graphic_path
        self.physics_fd = None
        self.static_fd = None
        self.graphic_fd = None
        self.physics_map = None
        self.static_map = None
        self.graphic_map = None
        self.physics = None
        self.static = None
        self.graphic = None

    def open(self):
        for path in (self.physics_path, self.static_path, self.graphic_path):
            if not os.path.exists(path):
                print(f"Waiting for AC shared memory: {path}")
                return False

        self.physics_fd = os.open(self.physics_path, os.O_RDONLY)
        self.static_fd = os.open(self.static_path, os.O_RDONLY)
        self.graphic_fd = os.open(self.graphic_path, os.O_RDONLY)
        self.physics_map = mmap.mmap(self.physics_fd, ctypes.sizeof(SPageFilePhysics), access=mmap.ACCESS_READ)
        self.static_map = mmap.mmap(self.static_fd, ctypes.sizeof(SPageFileStatic), access=mmap.ACCESS_READ)
        self.graphic_map = mmap.mmap(self.graphic_fd, ctypes.sizeof(SPageFileGraphic), access=mmap.ACCESS_READ)
        return True

    def read(self):
        if self.physics_map is None or self.static_map is None or self.graphic_map is None:
            return None

        # mmap.read() advances the internal file pointer, so reset before each read.
        self.physics_map.seek(0)
        physics_bytes = self.physics_map.read(ctypes.sizeof(SPageFilePhysics))
        physics_buffer = (ctypes.c_ubyte * ctypes.sizeof(SPageFilePhysics)).from_buffer_copy(physics_bytes)
        self.physics = ctypes.cast(ctypes.pointer(physics_buffer), ctypes.POINTER(SPageFilePhysics)).contents

        self.static_map.seek(0)
        static_bytes = self.static_map.read(ctypes.sizeof(SPageFileStatic))
        static_buffer = (ctypes.c_ubyte * ctypes.sizeof(SPageFileStatic)).from_buffer_copy(static_bytes)
        self.static = ctypes.cast(ctypes.pointer(static_buffer), ctypes.POINTER(SPageFileStatic)).contents

        self.graphic_map.seek(0)
        graphic_bytes = self.graphic_map.read(ctypes.sizeof(SPageFileGraphic))
        graphic_buffer = (ctypes.c_ubyte * ctypes.sizeof(SPageFileGraphic)).from_buffer_copy(graphic_bytes)
        self.graphic = ctypes.cast(ctypes.pointer(graphic_buffer), ctypes.POINTER(SPageFileGraphic)).contents

        return self._build_ac_sim_data()

    def _build_ac_sim_data(self):
        sim_data = SimData()
        sim_data.simstatus = 2

        if self.physics is None or self.static is None or self.graphic is None:
            sim_data.simstatus = 0
            return sim_data

        physics = self.physics
        static = self.static
        graphic = self.graphic

        sim_data.rpms = int(physics.rpms)
        sim_data.gear = int(physics.gear)
        sim_data.velocity = int(round(physics.speedKmh))

        sim_data.gas = float(physics.gas)
        sim_data.brake = float(physics.brake)
        sim_data.clutch = float(physics.clutch)
        sim_data.steer = float(physics.steerAngle)
        sim_data.handbrake = 0.0
        sim_data.fuel = float(physics.fuel)
        sim_data.brakebias = float(physics.brakeBias)
        sim_data.heading = float(physics.heading)
        sim_data.pitch = float(physics.pitch)
        sim_data.roll = float(physics.roll)
        sim_data.abs = float(physics.abs)
        sim_data.altitude = 1

        if sim_data.gear == 0:
            sim_data.gearc = "R"
        elif sim_data.gear == 1:
            sim_data.gearc = "N"
        else:
            sim_data.gearc = chr(sim_data.gear + 47)

        for index in range(4):
            sim_data.tyreRPS[index] = float(physics.wheelAngularSpeed[index])
            sim_data.tyrewear[index] = float(physics.tyreWear[index])
            sim_data.tyretemp[index] = float(physics.tyreCoreTemperature[index])
            sim_data.tyrepressure[index] = float(physics.wheelsPressure[index])
            sim_data.braketemp[index] = float(physics.brakeTemp[index])
            sim_data.tyreslipratio[index] = float(physics.SlipRatio[index])
            sim_data.tyreslipangle[index] = float(physics.SlipAngle[index])

        # AC's local velocity is Y-up (x=right, y=up, z=forward), so swap
        # y/z to match the app's Z-up convention - mirrors RFactor2Data.py's
        # equivalent swap for rF2's mLocalVel.
        sim_data.Xvelocity = physics.localVelocity.x
        sim_data.Zvelocity = physics.localVelocity.y
        sim_data.Yvelocity = physics.localVelocity.z

        sim_data.worldXvelocity = physics.velocity[0]
        sim_data.worldZvelocity = physics.velocity[1]
        sim_data.worldYvelocity = physics.velocity[2]

        sim_data.airdensity = float(physics.airDensity)
        sim_data.airtemp = float(physics.airTemp)
        sim_data.tracktemp = float(physics.roadTemp)

        sim_data.turboboostperct = float(physics.turboBoost)
        sim_data.maxturbo = float(static.MaxTurboBoost)
        sim_data.turboboost = sim_data.turboboostperct * sim_data.maxturbo

        maxrpm = int(static.maxRpm)
        sim_data.maxrpm = maxrpm if maxrpm > 0 else sim_data.rpms
        sim_data.fuelcapacity = float(static.maxFuel)

        for index in range(4):
            sim_data.tyrediameter[index] = float(static.tyreRadius[index]) * 2.0

        sim_data.lap = int(graphic.completedLaps)
        sim_data.position = int(graphic.position)
        sim_data.numlaps = int(graphic.numberOfLaps)
        sim_data.lastlap = ac_convert_to_simdata_laptime(int(graphic.iLastTime))
        sim_data.bestlap = ac_convert_to_simdata_laptime(int(graphic.iBestTime))
        sim_data.currentlap = ac_convert_to_simdata_laptime(int(graphic.iCurrentTime))
        sim_data.sectorindex = int(graphic.currentSectorIndex)
        sim_data.lastsectorinms = int(graphic.lastSectorTime)

        sim_data.session = int(graphic.session)
        sim_data.gamephase = int(graphic.status)

        # normalizedCarPosition/carCoordinates give player track position and
        # world position without needing the (out-of-scope) crewchief shared
        # memory segment that the rest of the AC telemetry ecosystem relies
        # on for this - see acsVehicleInfo.spLineLength in acdata.h.
        track_spline = float(static.TrackSPlineLength)
        player_spline = float(graphic.normalizedCarPosition)
        sim_data.playerspline = player_spline
        sim_data.trackspline = track_spline
        sim_data.trackdistancearound = spline_length_to_distance_around_track(track_spline, player_spline)
        sim_data.tracksamples = int(track_spline * 4) if track_spline > 0 else 0
        sim_data.playertrackpos = int(sim_data.trackdistancearound)

        sim_data.worldposx = float(graphic.carCoordinates[0])
        sim_data.worldposy = float(graphic.carCoordinates[1])
        sim_data.worldposz = float(graphic.carCoordinates[2])

        sim_data.car = self._decode_utf16(static.carModel)
        sim_data.track = self._decode_utf16(static.track)
        first_name = self._decode_utf16(static.playerName)
        last_name = self._decode_utf16(static.playerSurname)
        sim_data.driver = f"{first_name} {last_name}".strip()

        sim_data.numcars = int(static.numCars)

        # No crewchief segment (out of scope), so there's no full grid here -
        # only the player's own car, built from physics/graphic data above.
        sim_data.playercardata = self._build_ac_player_car_data(sim_data, graphic)

        return sim_data

    def _build_ac_player_car_data(self, sim_data, graphic):
        car_data = CarData()

        car_data.xpos = sim_data.worldposx
        car_data.ypos = sim_data.worldposy
        car_data.zpos = sim_data.worldposz
        car_data.carspline = sim_data.playerspline
        car_data.trackpos = int(sim_data.playerspline * 65535.0)

        car_data.speed = sim_data.velocity
        car_data.lap = sim_data.lap
        car_data.place = sim_data.position

        car_data.lastlap = sim_data.lastlap
        car_data.bestlap = sim_data.bestlap

        car_data.inpit = bool(graphic.isInPit)
        car_data.inpitlane = bool(graphic.IsInPitLane)

        car_data.driver = sim_data.driver
        car_data.car = sim_data.car

        return car_data

    def _decode_utf16(self, value):
        try:
            raw_bytes = bytes(value)
        except (TypeError, ValueError):
            return ""
        return raw_bytes.decode("utf-16-le", errors="ignore").split("\x00", 1)[0]

    def close(self):
        if self.physics_map:
            self.physics_map.close()
        if self.static_map:
            self.static_map.close()
        if self.graphic_map:
            self.graphic_map.close()
        if self.physics_fd is not None:
            os.close(self.physics_fd)
        if self.static_fd is not None:
            os.close(self.static_fd)
        if self.graphic_fd is not None:
            os.close(self.graphic_fd)
