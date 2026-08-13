import ctypes
from SimData import *
import os
import mmap
import ctypes

RF2_TELEMETRY_PATH = "/dev/shm/$rFactor2SMMP_Telemetry$"
RF2_SCORING_PATH = "/dev/shm/$rFactor2SMMP_Scoring$"

RF2_DEBUG_TELEMETRY_PATH = "$rFactor2SMMP_Telemetry$"
RF2_DEBUG_SCORING_PATH = "$rFactor2SMMP_Scoring$"

def rf2_convert_to_simdata_laptime(rf2_laptime):
    if rf2_laptime <= 0:
        return LapTime(hours=0, minutes=0, seconds=0, fraction=0)

    hours = int(rf2_laptime // 3600)
    minutes = int((rf2_laptime % 3600) // 60)
    seconds = int(rf2_laptime % 60)
    fraction = int(round((rf2_laptime - int(rf2_laptime)) * 1000.0))
    if fraction < 0:
        fraction = 0
    if fraction > 999:
        fraction = 999
    return LapTime(hours=hours, minutes=minutes, seconds=seconds, fraction=fraction)


def rf2_flag_to_simdata_flag(rf2_flag):
    if rf2_flag == 6:
        return 4
    return 0


class GamePhase:
    """rFactor2 mGamePhase values, as observed for sim_data.gamephase.

    This is a race-control flag state (green/yellow/stopped/paused/etc.),
    not a session-type indicator - it can't reliably distinguish qualifying
    from practice/race (e.g. qualifying sessions report SESSION_OVER (8)
    while a qualifying lap is actually in progress). Use Session (mSession /
    sim_data.session) for practice/qualifying/race/warmup checks instead.
    """

    BEFORE_SESSION = 0
    RECON_LAPS = 1  # race only
    GRID_WALK = 2  # race only
    FORMATION_LAP = 3  # race only
    COUNTDOWN = 4  # race only
    GREEN_FLAG = 5
    FULL_COURSE_YELLOW = 6
    SESSION_STOPPED = 7
    SESSION_OVER = 8
    PAUSED = 9


class Session:
    """rFactor2 mSession values, as observed for sim_data.session.

    Unlike GamePhase (a race-control flag state), this directly encodes the
    session type and reliably distinguishes practice/qualifying/race/warmup.
    """

    TEST_DAY = 0
    PRACTICE_MIN = 1
    PRACTICE_MAX = 4
    QUALIFYING_MIN = 5
    QUALIFYING_MAX = 8
    WARMUP = 9
    RACE_MIN = 10
    RACE_MAX = 13

    @staticmethod
    def is_practice(session):
        return Session.PRACTICE_MIN <= session <= Session.PRACTICE_MAX

    @staticmethod
    def is_qualifying(session):
        return Session.QUALIFYING_MIN <= session <= Session.QUALIFYING_MAX

    @staticmethod
    def is_race(session):
        return Session.RACE_MIN <= session <= Session.RACE_MAX


def _coerce_int_value(value):
    if isinstance(value, (bytes, bytearray)):
        return value[0] if value else 0
    if hasattr(value, "value"):
        val = value.value
        if isinstance(val, (bytes, bytearray)):
            if not val:
                return 0
            # Try to decode printable bytes (like b'0x5' or b'5') and parse as int
            try:
                s = val.split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
            except Exception:
                s = ""
            if s:
                try:
                    return int(s, 0)
                except (TypeError, ValueError):
                    pass
            # Fallback: raw ordinal of first byte
            return val[0]
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

class rF2Vec3(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("z", ctypes.c_double),
    ]
    _pack_ = 4


class TelemWheelV01(ctypes.Structure):
    _fields_ = [
        ("mSuspensionDeflection", ctypes.c_double),
        ("mRideHeight", ctypes.c_double),
        ("mSuspForce", ctypes.c_double),
        ("mBrakeTemp", ctypes.c_double),
        ("mBrakePressure", ctypes.c_double),
        ("mRotation", ctypes.c_double),
        ("mLateralPatchVel", ctypes.c_double),
        ("mLongitudinalPatchVel", ctypes.c_double),
        ("mLateralGroundVel", ctypes.c_double),
        ("mLongitudinalGroundVel", ctypes.c_double),
        ("mCamber", ctypes.c_double),
        ("mLateralForce", ctypes.c_double),
        ("mLongitudinalForce", ctypes.c_double),
        ("mTireLoad", ctypes.c_double),
        ("mGripFract", ctypes.c_double),
        ("mPressure", ctypes.c_double),
        ("mTemperature", ctypes.c_double * 3),
        ("mWear", ctypes.c_double),
        ("mTerrainName", ctypes.c_char * 16),
        ("mSurfaceType", ctypes.c_ubyte),
        ("mFlat", ctypes.c_bool),
        ("mDetached", ctypes.c_bool),
        ("mStaticUndeflectedRadius", ctypes.c_ubyte),
        ("mVerticalTireDeflection", ctypes.c_double),
        ("mWheelYLocation", ctypes.c_double),
        ("mToe", ctypes.c_double),
        ("mTireCarcassTemperature", ctypes.c_double),
        ("mTireInnerLayerTemperature", ctypes.c_double * 3),
        ("mExpansion", ctypes.c_ubyte * 24),
    ]
    _pack_ = 4


class rF2VehicleTelemetry(ctypes.Structure):
    _fields_ = [
        ("mID", ctypes.c_int),
        ("mDeltaTime", ctypes.c_double),
        ("mElapsedTime", ctypes.c_double),
        ("mLapNumber", ctypes.c_int),
        ("mLapStartET", ctypes.c_double),
        ("mVehicleName", ctypes.c_char * 64),
        ("mTrackName", ctypes.c_char * 64),
        ("mPos", rF2Vec3),
        ("mLocalVel", rF2Vec3),
        ("mLocalAccel", rF2Vec3),
        ("mOri", rF2Vec3 * 3),
        ("mLocalRot", rF2Vec3),
        ("mLocalRotAccel", rF2Vec3),
        ("mGear", ctypes.c_int),
        ("mEngineRPM", ctypes.c_double),
        ("mEngineWaterTemp", ctypes.c_double),
        ("mEngineOilTemp", ctypes.c_double),
        ("mClutchRPM", ctypes.c_double),
        ("mUnfilteredThrottle", ctypes.c_double),
        ("mUnfilteredBrake", ctypes.c_double),
        ("mUnfilteredSteering", ctypes.c_double),
        ("mUnfilteredClutch", ctypes.c_double),
        ("mFilteredThrottle", ctypes.c_double),
        ("mFilteredBrake", ctypes.c_double),
        ("mFilteredSteering", ctypes.c_double),
        ("mFilteredClutch", ctypes.c_double),
        ("mSteeringShaftTorque", ctypes.c_double),
        ("mFront3rdDeflection", ctypes.c_double),
        ("mRear3rdDeflection", ctypes.c_double),
        ("mFrontWingHeight", ctypes.c_double),
        ("mFrontRideHeight", ctypes.c_double),
        ("mRearRideHeight", ctypes.c_double),
        ("mDrag", ctypes.c_double),
        ("mFrontDownforce", ctypes.c_double),
        ("mRearDownforce", ctypes.c_double),
        ("mFuel", ctypes.c_double),
        ("mEngineMaxRPM", ctypes.c_double),
        ("mScheduledStops", ctypes.c_ubyte),
        ("mOverheating", ctypes.c_bool),
        ("mDetached", ctypes.c_bool),
        ("mHeadlights", ctypes.c_bool),
        ("mDentSeverity", ctypes.c_ubyte * 8),
        ("mLastImpactET", ctypes.c_double),
        ("mLastImpactMagnitude", ctypes.c_double),
        ("mLastImpactPos", rF2Vec3),
        ("mEngineTorque", ctypes.c_double),
        ("mCurrentSector", ctypes.c_int),
        ("mSpeedLimiter", ctypes.c_ubyte),
        ("mMaxGears", ctypes.c_ubyte),
        ("mFrontTireCompoundIndex", ctypes.c_ubyte),
        ("mRearTireCompoundIndex", ctypes.c_ubyte),
        ("mFuelCapacity", ctypes.c_double),
        ("mFrontFlapActivated", ctypes.c_ubyte),
        ("mRearFlapActivated", ctypes.c_ubyte),
        ("mRearFlapLegalStatus", ctypes.c_ubyte),
        ("mIgnitionStarter", ctypes.c_ubyte),
        ("mFrontTireCompoundName", ctypes.c_char * 18),
        ("mRearTireCompoundName", ctypes.c_char * 18),
        ("mSpeedLimiterAvailable", ctypes.c_ubyte),
        ("mAntiStallActivated", ctypes.c_ubyte),
        ("mUnused", ctypes.c_ubyte * 2),
        ("mVisualSteeringWheelRange", ctypes.c_float),
        ("mRearBrakeBias", ctypes.c_double),
        ("mTurboBoostPressure", ctypes.c_double),
        ("mPhysicsToGraphicsOffset", ctypes.c_float * 3),
        ("mPhysicalSteeringWheelRange", ctypes.c_float),
        ("mExpansion", ctypes.c_ubyte * 152),
        ("mWheel", TelemWheelV01 * 4),
    ]
    _pack_ = 4


class rF2ScoringInfo(ctypes.Structure):
    _fields_ = [
        ("mTrackName", ctypes.c_ubyte * 64),
        ("mSession", ctypes.c_int),
        ("mCurrentET", ctypes.c_double),
        ("mEndET", ctypes.c_double),
        ("mMaxLaps", ctypes.c_int),
        ("mLapDist", ctypes.c_double),
        ("pointer1", ctypes.c_ubyte * 8),
        ("mNumVehicles", ctypes.c_int),
        ("mGamePhase", ctypes.c_char),
        ("YellowFlagState", ctypes.c_char),
        ("mSectorFlag", ctypes.c_char * 3),
        ("mStartLight", ctypes.c_char),
        ("mNumRedLights", ctypes.c_char),
        ("mInRealtime", ctypes.c_char),
        ("mPlayerName", ctypes.c_char * 32),
        ("mPlrFileName", ctypes.c_char * 64),
        ("mDarkCloud", ctypes.c_double),
        ("mRaining", ctypes.c_double),
        ("mAmbientTemp", ctypes.c_double),
        ("mTrackTemp", ctypes.c_double),
        ("mWind", rF2Vec3),
        ("mMinPathWetness", ctypes.c_double),
        ("mMaxPathWetness", ctypes.c_double),
        ("mExpansion", ctypes.c_char * 256),
        ("pointer2", ctypes.c_char * 8),
    ]
    _pack_ = 4


class rF2VehicleScoring(ctypes.Structure):
    _fields_ = [
        ("mID", ctypes.c_int),
        ("mDriverName", ctypes.c_char * 32),
        ("mVehicleName", ctypes.c_char * 64),
        ("mTotalLaps", ctypes.c_short),
        ("mSector", ctypes.c_char),
        ("mFinishStatus", ctypes.c_char),
        ("mLapDist", ctypes.c_double),
        ("mPathLateral", ctypes.c_double),
        ("mTrackEdge", ctypes.c_double),
        ("mBestSector1", ctypes.c_double),
        ("mBestSector2", ctypes.c_double),
        ("mBestLapTime", ctypes.c_double),
        ("mLastSector1", ctypes.c_double),
        ("mLastSector2", ctypes.c_double),
        ("mLastLapTime", ctypes.c_double),
        ("mCurSector1", ctypes.c_double),
        ("mCurSector2", ctypes.c_double),
        ("mNumPitstops", ctypes.c_short),
        ("mNumPenalties", ctypes.c_short),
        ("mIsPlayer", ctypes.c_bool),
        ("mControl", ctypes.c_char),
        ("mInPits", ctypes.c_bool),
        ("mPlace", ctypes.c_ubyte),
        ("mVehicleClass", ctypes.c_char * 32),
        ("mTimeBehindNext", ctypes.c_double),
        ("mLapsBehindNext", ctypes.c_int),
        ("mTimeBehindLeader", ctypes.c_double),
        ("mLapsBehindLeader", ctypes.c_int),
        ("mLapStartET", ctypes.c_double),
        ("mPos", rF2Vec3),
        ("mLocalVel", rF2Vec3),
        ("mLocalAccel", rF2Vec3),
        ("mOri", rF2Vec3 * 3),
        ("mLocalRot", rF2Vec3),
        ("mLocalRotAccel", rF2Vec3),
        ("mHeadlights", ctypes.c_ubyte),
        ("mPitState", ctypes.c_ubyte),
        ("mServerScored", ctypes.c_ubyte),
        ("mIndividualPhase", ctypes.c_ubyte),
        ("mQualification", ctypes.c_int),
        ("mTimeIntoLap", ctypes.c_double),
        ("mEstimatedLapTime", ctypes.c_double),
        ("mPitGroup", ctypes.c_char * 24),
        ("mFlag", ctypes.c_ubyte),
        ("mUnderYellow", ctypes.c_bool),
        ("mCountLapFlag", ctypes.c_ubyte),
        ("mInGarageStall", ctypes.c_bool),
        ("mUpgradePack", ctypes.c_ubyte * 16),
        ("mPitLapDist", ctypes.c_float),
        ("mBestLapSector1", ctypes.c_float),
        ("mBestLapSector2", ctypes.c_float),
        ("mExpansion", ctypes.c_ubyte * 48),
    ]
    _pack_ = 4


class rF2Telemetry(ctypes.Structure):
    _fields_ = [
        ("mVersionUpdateBegin", ctypes.c_int),
        ("mVersionUpdateEnd", ctypes.c_int),
        ("mBytesUpdatedHint", ctypes.c_int),
        ("mNumVehicles", ctypes.c_int),
        ("mVehicles", rF2VehicleTelemetry * 64),
    ]
    _pack_ = 4


class rF2Scoring(ctypes.Structure):
    _fields_ = [
        ("mVersionUpdateBegin", ctypes.c_int),
        ("mVersionUpdateEnd", ctypes.c_int),
        ("mBytesUpdatedHint", ctypes.c_int),
        ("mScoringInfo", rF2ScoringInfo),
        ("mVehicles", rF2VehicleScoring * 64),
    ]
    _pack_ = 4

class RF2TelemetryReader:
    def __init__(self, telemetry_path=RF2_TELEMETRY_PATH, scoring_path=RF2_SCORING_PATH):
        self.telemetry_path = telemetry_path
        self.scoring_path = scoring_path
        self.telemetry_fd = None
        self.scoring_fd = None
        self.telemetry_map = None
        self.scoring_map = None
        self.telemetry = None
        self.scoring = None
        self.simData = SimData()
        self.CarData = CarData()

    def open(self):
        if not os.path.exists(self.telemetry_path):
            print(f"Waiting for rf2 telemetry shared memory: {self.telemetry_path}")
            return False
        if not os.path.exists(self.scoring_path):
            print(f"Waiting for rf2 scoring shared memory: {self.scoring_path}")
            return False

        self.telemetry_fd = os.open(self.telemetry_path, os.O_RDONLY)
        self.scoring_fd = os.open(self.scoring_path, os.O_RDONLY)
        self.telemetry_map = mmap.mmap(self.telemetry_fd, ctypes.sizeof(rF2Telemetry), access=mmap.ACCESS_READ)
        self.scoring_map = mmap.mmap(self.scoring_fd, ctypes.sizeof(rF2Scoring), access=mmap.ACCESS_READ)
        return True

    def read(self):
        if self.telemetry_map is None or self.scoring_map is None:
            return None

        # mmap.read() advances the internal file pointer, so reset before each read.
        self.telemetry_map.seek(0)
        telemetry_bytes = self.telemetry_map.read(ctypes.sizeof(rF2Telemetry))
        telemetry_buffer = (ctypes.c_ubyte * ctypes.sizeof(rF2Telemetry)).from_buffer_copy(telemetry_bytes)
        self.telemetry = ctypes.cast(ctypes.pointer(telemetry_buffer), ctypes.POINTER(rF2Telemetry)).contents

        self.scoring_map.seek(0)
        scoring_bytes = self.scoring_map.read(ctypes.sizeof(rF2Scoring))
        scoring_buffer = (ctypes.c_ubyte * ctypes.sizeof(rF2Scoring)).from_buffer_copy(scoring_bytes)
        self.scoring = ctypes.cast(ctypes.pointer(scoring_buffer), ctypes.POINTER(rF2Scoring)).contents

        self.SimData = self._build_rfactor2_sim_data()

        return self.SimData

    def _build_rfactor2_sim_data(self):
        sim_data = SimData()
        sim_data.simstatus = 2

        if self.telemetry is None or self.scoring is None:
            sim_data.simstatus = 0
            return sim_data

        player_index = 0
        scoring_count = int(self.scoring.mScoringInfo.mNumVehicles)
        for index in range(min(scoring_count, 64)):
            if self.scoring.mVehicles[index].mIsPlayer:
                player_index = index
                break

        vehicle = self.telemetry.mVehicles[player_index]
        scoring_vehicle = self.scoring.mVehicles[player_index]

        #sim_data.playerVehicle = scoring_vehicle


        if hasattr(vehicle, "mLocalVel"):
            sim_data.velocity = int(abs(round(3.6 * vehicle.mLocalVel.z)))
            sim_data.Xvelocity = vehicle.mLocalVel.x
            sim_data.Yvelocity = vehicle.mLocalVel.y
            sim_data.Zvelocity = vehicle.mLocalVel.z

        sim_data.rpms = int(vehicle.mEngineRPM)
        sim_data.gear = int(vehicle.mGear)
        sim_data.maxrpm = int(round(vehicle.mEngineMaxRPM))
        sim_data.gas = float(vehicle.mUnfilteredThrottle)
        sim_data.brake = float(vehicle.mUnfilteredBrake)
        sim_data.clutch = float(vehicle.mUnfilteredClutch)
        sim_data.steer = float(vehicle.mUnfilteredSteering)
        sim_data.fuel = float(vehicle.mFuel)
        sim_data.fuelcapacity = float(vehicle.mFuelCapacity)
        sim_data.brakebias = float(vehicle.mRearBrakeBias)
        sim_data.altitude = 1

        for index in range(4):
            wheel = vehicle.mWheel[index]
            sim_data.tyreRPS[index] = -1.0 * wheel.mRotation
            sim_data.tyrewear[index] = wheel.mWear
            sim_data.tyretemp[index] = wheel.mTireCarcassTemperature - 273.15
            sim_data.braketemp[index] = wheel.mBrakeTemp
            sim_data.tyrepressure[index] = wheel.mPressure

        sim_data.worldXvelocity = (vehicle.mOri[0].x * vehicle.mLocalVel.x) + (vehicle.mOri[0].z * vehicle.mLocalVel.y) + (vehicle.mOri[0].y * vehicle.mLocalVel.z)
        sim_data.worldYvelocity = (vehicle.mOri[2].x * vehicle.mLocalVel.x) + (vehicle.mOri[2].z * vehicle.mLocalVel.y) + (vehicle.mOri[2].y * vehicle.mLocalVel.z)
        sim_data.worldZvelocity = (vehicle.mOri[1].x * vehicle.mLocalVel.x) + (vehicle.mOri[1].z * vehicle.mLocalVel.y) + (vehicle.mOri[1].y * vehicle.mLocalVel.z)

        sim_data.Xvelocity *= -1.0
        sim_data.Yvelocity *= -1.0
        sim_data.Zvelocity *= -1.0

        sim_data.airtemp = float(self.scoring.mScoringInfo.mAmbientTemp)
        sim_data.tracktemp = float(self.scoring.mScoringInfo.mTrackTemp)

        trackdist = float(self.scoring.mScoringInfo.mLapDist)
        pos = float(scoring_vehicle.mLapDist)
        if pos < 0:
            pos = 0.0
        sim_data.tracksamples = int(trackdist * 4) if trackdist > 0 else 0
        sim_data.playerspline = pos / trackdist if trackdist > 0 else 0.0

        sim_data.lap = int(vehicle.mLapNumber) + 1
        sim_data.position = int(scoring_vehicle.mPlace)
        sim_data.lastlap = rf2_convert_to_simdata_laptime(scoring_vehicle.mLastLapTime)
        sim_data.bestlap = rf2_convert_to_simdata_laptime(scoring_vehicle.mBestLapTime)
        sim_data.currentlap = rf2_convert_to_simdata_laptime(scoring_vehicle.mTimeIntoLap)
        sim_data.numlaps = int(self.scoring.mScoringInfo.mMaxLaps)
        sim_data.sectorindex = _coerce_int_value(scoring_vehicle.mSector)
        sim_data.playerflag = _coerce_int_value(scoring_vehicle.mFlag)
        sim_data.gamephase = _coerce_int_value(self.scoring.mScoringInfo.mGamePhase)
        sim_data.session = _coerce_int_value(self.scoring.mScoringInfo.mSession)
        sim_data.sessiontime = rf2_convert_to_simdata_laptime(vehicle.mElapsedTime)

        sim_data.car = self._decode_string(vehicle.mVehicleName)
        sim_data.track = self._decode_string(self.scoring.mScoringInfo.mTrackName)
        sim_data.driver = self._decode_string(scoring_vehicle.mDriverName)
        sim_data.tyrecompound = self._decode_string(vehicle.mFrontTireCompoundName)

        sim_data.numcars = int(self.telemetry.mNumVehicles)
        sim_data.worldposx = vehicle.mPos.x
        sim_data.worldposy = vehicle.mPos.y
        sim_data.worldposz = vehicle.mPos.z

        sim_data.playercardata = self._build_rfactor2_car_data(vehicle, scoring_vehicle)

        grid_count = min(scoring_count, int(self.telemetry.mNumVehicles), 64, MAXCARS)
        sim_data.cars = [
            self._build_rfactor2_car_data(self.telemetry.mVehicles[index], self.scoring.mVehicles[index])
            for index in range(grid_count)
        ]
        sim_data.numcars = grid_count

        return sim_data

    def _build_rfactor2_car_data(self, vehicle, scoring_vehicle):
        """Map rF2 vehicle/scoring telemetry into a generic CarData struct."""
        car_data = CarData()

        car_data.xpos = vehicle.mPos.x
        car_data.ypos = vehicle.mPos.y
        car_data.zpos = vehicle.mPos.z

        trackdist = float(self.scoring.mScoringInfo.mLapDist)
        lap_distance = float(scoring_vehicle.mLapDist)
        car_data.carspline = lap_distance / trackdist if trackdist > 0 else 0.0
        car_data.trackpos = int(car_data.carspline * 65535.0) if trackdist > 0 else 0

        car_data.speed = float(abs(round(3.6 * vehicle.mLocalVel.z)))
        car_data.pos = int(lap_distance)
        car_data.lap = int(vehicle.mLapNumber) + 1
        car_data.place = int(scoring_vehicle.mPlace)
        car_data.timebehindleader = float(scoring_vehicle.mTimeBehindLeader)

        car_data.lastlap = rf2_convert_to_simdata_laptime(scoring_vehicle.mLastLapTime)
        car_data.bestlap = rf2_convert_to_simdata_laptime(scoring_vehicle.mBestLapTime)

        car_data.inpit = bool(scoring_vehicle.mInPits)
        car_data.inpitlane = bool(scoring_vehicle.mInPits)
        car_data.ingarage = bool(getattr(scoring_vehicle, 'mInGarageStall', False))
        car_data.inpitentrance = False
        car_data.inpitexit = False
        car_data.inpitstopped = False

        car_data.driver = self._decode_string(scoring_vehicle.mDriverName)
        car_data.car = self._decode_string(vehicle.mVehicleName)

        return car_data

    def _build_laptime_data(self):
        LapTime = LapTime()

        return LapTime


    def _decode_string(self, value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.rstrip("\x00")

        if isinstance(value, (bytes, bytearray)):
            raw_bytes = bytes(value)
        elif hasattr(value, "value"):
            raw_value = value.value
            if isinstance(raw_value, str):
                return raw_value.rstrip("\x00")
            if isinstance(raw_value, (bytes, bytearray)):
                raw_bytes = bytes(raw_value)
            else:
                try:
                    raw_bytes = bytes(raw_value)
                except (TypeError, ValueError):
                    return str(raw_value)
        else:
            try:
                raw_bytes = bytes(value)
            except (TypeError, ValueError):
                try:
                    raw_bytes = bytearray(value)
                except (TypeError, ValueError):
                    return str(value)

        if not raw_bytes:
            return ""
        return raw_bytes.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")

    def close(self):
        if self.telemetry_map:
            self.telemetry_map.close()
        if self.scoring_map:
            self.scoring_map.close()
        if self.telemetry_fd is not None:
            os.close(self.telemetry_fd)
        if self.scoring_fd is not None:
            os.close(self.scoring_fd)