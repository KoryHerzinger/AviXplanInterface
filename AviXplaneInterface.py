# decompyle3 version 3.9.1.dev0
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.8.10 (tags/v3.8.10:3d8993a, May  3 2021, 11:48:03) [MSC v.1928 64 bit (AMD64)]
# Embedded file name: AviXplaneInterface.py
# Compiled at: 2023-06-16 15:24:26
import os, time, socket, struct, binascii, sys, math, threading, XavionReceiver
try:
    import configparser
except:
    import ConfigParser as configparser
finally:
    try:
        import exceptions
    except ImportError:
        import builtins as exceptions
    finally:
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        import AviGeoid
        try:
            import AviXplaneUdp
        except:
            import AviXPlaneUdp as AviXplaneUdp
            raise
        finally:
            import XPlaneUdp, PyImportSimInterface as SimApi, re, argparse
            g_chassisId = 0
            try:
                import win32api
            except:
                print('win32api not installed, exits may leave stray subscriptions')
            finally:

                def on_exit(sig, func=None):
                    Shutdown()
                    time.sleep(0.5)

                win32api.SetConsoleCtrlHandler(on_exit, True)
            dllLock = threading.RLock()
            gAviGeoid = AviGeoid.AviGeoid()
            g_axPlane = None
            g_xavionRepeater = None
            g_xavionReceiver = None

            def get_version_str():
                majorAndMinorVersion = '0.1'
                p4Rev = 'unk'
                p4Version = '$Revision: #12 $'
                match = re.search('\\#([0-9]+)', p4Version)
                if match is not None:
                    p4Rev = match.group(1)
                return '{0}.{1}+'.format(majorAndMinorVersion, p4Rev)


            radioModels = [
             ('Nav1StandbyFreq', 'nav1_standby_frequency', 'nav2_freq'),
             ('Nav2Freq', 'nav2_frequency', 'nav2_freq'),
             ('Nav1ActiveFreq', 'nav1_frequency', 'nav1_freq'),
             ('Com1StandbyFreq', 'com1_standby_frequency', 'com2_freq'),
             ('Com1ActiveFreq', 'com1_frequency', 'com1_freq')]
            radioModels1 = [
             ('Nav1StandbyFreq', 'nav1_standby_frequency', 'nav2_freq'),
             ('Nav2Freq', 'nav2_frequency', 'nav2_freq'),
             ('Nav1ActiveFreq', 'nav1_frequency', 'nav1_freq'),
             ('Com1StandbyFreq', 'com1_standby_frequency', 'com2_freq'),
             ('Com1ActiveFreq', 'com1_frequency', 'com1_freq')]
            radioModels2 = [
             ('Nav1StandbyFreq', 'nav1_standby_frequency', 'nav2_freq'),
             ('Nav2Freq', 'nav2_frequency', 'nav2_freq'),
             ('Nav1ActiveFreq', 'nav1_frequency', 'nav1_freq'),
             ('Com1StandbyFreq', 'com1_standby_frequency', 'com2_freq'),
             ('Com1ActiveFreq', 'com1_frequency', 'com1_freq')]
            
            def deg_180(headingIn):
                if headingIn > 180:
                    headingOut = headingIn - 360
                else:
                    headingOut = headingIn
                return headingOut


            def deg_pi(headingIn):
                headingIn = headingIn % (2 * math.pi)
                if headingIn > math.pi:
                    headingOut = headingIn - 2 * math.pi
                else:
                    headingOut = headingIn % (2 * math.pi)
                return headingOut


            def deg_360(headingIn):
                return headingIn % 360.0


            class FirstOrderFilter(object):
                __doc__ = 'Functor for first order exponential filter'

                def __init__(self, tau):
                    self.tau = tau
                    self.one_over_tau = 1.0 / tau
                    self.reset()

                def reset(self):
                    self.filter_time = 0
                    self.filter_val = None

                def __call__(self, sample_val):
                    now = time.time()
                    if self.filter_val is None:
                        self.filter_time = now
                        self.filter_val = sample_val
                    else:
                        delta_t = now - self.filter_time
                        filter_param = delta_t * self.one_over_tau
                        if delta_t > 0:
                            self.filter_val = self.filter_val + (self.filter_val - sample_val) * filter_param
                            self.filter_time = now


            g_pposCount = 0

            def on_ppos(aviXplaneUdpObj, data):
                global g_pposCount
                keys = [
                 'agl','pitch','psi','roll','p','q','r']
                vn = data['vn']
                ve = data['ve']
                vu = data['vu']
                lat = data['lat']
                lon = data['lon']
                msl = data['msl']
                gs = math.sqrt(vn ** 2 + ve ** 2)
                trk = math.atan2(ve, vn)
                antennaOffsetHeight = 2.0
                hae = msl + gAviGeoid.wgs84_hae_m(lat, lon) + antennaOffsetHeight
                agl = data['agl']
                if g_pposCount % 5 == 0:
                    set_sim_param(None, lat, 'Gps.Latitude')
                    set_sim_param(None, lon, 'Gps.Longitude')
                    set_sim_param(None, hae, 'Gps.Altitude')
                    set_sim_param(None, vn, 'Gps.NVel')
                    set_sim_param(None, ve, 'Gps.EVel')
                    set_sim_param(None, vu, 'Gps.VVel')
                if g_pposCount >= 15:
                    g_pposCount = 0
                set_sim_param(None, math.radians(data['pitch']) / 2, 'AHRS.Pitch')
                set_sim_param(None, math.radians(data['roll']), 'AHRS.Roll')
                set_sim_param(None, math.radians(data['pitch']) / 2, 'AHRS.Pitch')
                set_sim_param(None, math.degrees(data['p']), 'AHRS.PitchRate')
                set_sim_param(None, math.degrees(data['q']), 'AHRS.RollRate')
                set_sim_param(None, math.degrees(data['r']), 'AHRS.YawRate')
                set_sim_param(None, math.degrees(data['r']), 'AHRS.HeadingRate')
                g_pposCount += 1
                with dllLock:
                    sync = g_SimInterface.sync_sim(False)
            

            def on_msl_elevation(aviXplaneUdpObj, datum, fieldName):
                global g_axPlane
                msl = datum
                antennaOffsetHeight = 2.0
                lat = 0.0
                lon = 0.0
                try:
                    lat = g_axPlane.params['Gps.Latitude']
                    lon = g_axPlane.params['Gps.Longitude']
                except:
                    print('Could not find GPS lat/lon information')
                else:
                    hae = msl + gAviGeoid.wgs84_hae_m(lat, lon) + antennaOffsetHeight
                    set_sim_param(None, hae, 'Gps.Altitude')


            def set_sim_param_and_sync(aviXplaneUdpObj, datum, fieldName):
                with dllLock:
                    success = g_SimInterface.set_sim(fieldName, datum)
                    sync = g_SimInterface.sync_sim(False)
                    if not success:
                        print('failed to set: {0}-- {1}'.format(fieldName, g_SimInterface.clear_last_error()))


            class EitherDatum(object):

                def __init__(self, conditionFunction, handlerA, handlerB=None):
                    self.handlerA = handlerA
                    self.handlerB = handlerB
                    self.conditionFunction = conditionFunction

                def __call__(self, aviXplaneUdpObj, datum, fieldName):
                    if self.conditionFunction():
                        return self.handlerA(aviXplaneUdpObj, self.modification(datum), fieldName)
                    if self.handlerB is not None:
                        return self.handlerB(aviXplaneUdpObj, self.modification(datum), fieldName)


            class ModifyDatum(object):

                def __init__(self, nextFunction, modification):
                    self.nextFunction = nextFunction
                    self.modification = modification

                def __call__(self, aviXplaneUdpObj, datum, fieldName):
                    return self.nextFunction(aviXplaneUdpObj, self.modification(datum), fieldName)


            def ClampNearZeroGenerator(clampBelowAbs):
                func = lambda x: 0 if abs(x) < clampBelowAbs else x
                return func

#            def ClampNearZeroGenerator(clampBelow):
#                func = lambda x: 0 if abs(x) < clampBelowAbs else x
#                return func


            def set_sim_param(aviXplaneUdpObj, datum, fieldName):
                with dllLock:
                    success = g_SimInterface.set_sim(fieldName, datum)
                    if not success:
                        print('failed to set: {0}--{1} {2}'.format(fieldName, datum, g_SimInterface.clear_last_error()))


            def get_sim_param(aviXplaneUdpObj, fieldName):
                return g_SimInterface.set_sim(fieldName)


            def display_param(aviXplaneUdpObj, datum, fieldName):
                print('Got {0}! {1} t: {2}'.format(fieldName, datum, time.time()))


            def print_param(aviXplaneUdpObj, datum, fieldName):
                print('Got Param: {0} {1}'.format(fieldName, datum))


            def store_param(aviXplaneUdpObj, datum, fieldName):
                g_axPlane.params[fieldName] = datum
            

            def store_string_param(aviXplaneUdpObj, datum, fieldName):
                """
                field name MUST be in the format:
                    fieldName[x] where [x] is the character's position in the string
                    if x is larger than the string, the string will be padded with spaces
                """
                strFieldName, strIndex = fieldName.strip(']').split('[')
                listFieldName = strFieldName + '_list'
                intIndex = int(strIndex)
                try:
                    currentVal = aviXplaneUdpObj.params[listFieldName]
                except:
                    aviXplaneUdpObj.params[listFieldName] = []
                else:
                    padCount = intIndex + 1 - len(aviXplaneUdpObj.params[listFieldName])
                    if padCount > 0:
                        aviXplaneUdpObj.params[listFieldName].append(' ' * padCount)
                    aviXplaneUdpObj.params[listFieldName][intIndex] = chr(int(datum))
                    nullTermIndex = len(aviXplaneUdpObj.params[listFieldName])
                    if '\x00' in aviXplaneUdpObj.params[listFieldName]:
                        nullTermIndex = aviXplaneUdpObj.params[listFieldName].index('\x00')
                    aviXplaneUdpObj.params[strFieldName] = ''.join(aviXplaneUdpObj.params[listFieldName][:nullTermIndex])


            g_runningThreads = True

            def read_from_ifd_thread():
                global g_chassisId
                global g_runningThreads
                prevValuesIfd = {}
                prevValuesXplane = {}
                prevXplaneNavMode = 2
                prevIfdNavMode = -1
                runcount = 0
                lastVlocGuidanceState = False
                lastRollCmdOverride = None
                lastApproachModeActive = None
                while g_runningThreads:
                    rateGroup1Hz = runcount % 10 == 0
                    rateGroup2Hz = runcount % 5 == 0
                    rateGroup5Hz = runcount % 2 == 0
                    rateGroup10Hz = True
                    runcount += 1
                    with dllLock:
                        g_SimInterface.sync_sim(False)
                    if rateGroup5Hz:
                        ifdSelectedCourse = g_SimInterface.get_sim('IfdRadio.selected_course')
                        ifdDtk = g_SimInterface.get_sim('IfdRadio.desired_track')
                        ifdRollCmd = g_SimInterface.get_sim('IfdRadio.roll_command')
                        if g_chassisId == 0:
                            g_axPlane.set_dataref('sim/cockpit/radios/gps_course_degtm', ifdSelectedCourse)
                            xplaneApInGpss = g_axPlane.params['xplaneApGpssMode'] == 2
                            xplaneApInApproachOrArmed = g_axPlane.params['xplaneApApproachStatus'] > 0
                            if xplaneApInGpss and ifdRollCmd >= -60.0 and ifdRollCmd <= 60.0:
                                g_axPlane.set_dataref('sim/cockpit/autopilot/flight_director_roll', ifdRollCmd)
                                rollCmdOverride = True
                            else:
                                rollCmdOverride = False
                            if lastRollCmdOverride != rollCmdOverride:
                                g_axPlane.set_dataref('sim/operation/override/override_flightdir_roll', 1 if rollCmdOverride else 0)
                                lastRollCmdOverride = rollCmdOverride
                            if xplaneApInApproachOrArmed:
                                if not lastApproachModeActive:
                                    g_axPlane.set_dataref('sim/cockpit2/autopilot/heading_dial_deg_mag_pilot', ifdSelectedCourse)
                                    g_axPlane.set_dataref('sim/cockpit/radios/gps_slope_degt', 3.0)
                            lastApproachModeActive = xplaneApInApproachOrArmed
                        else:
                            g_axPlane.set_dataref('sim/cockpit/radios/gps_course_degtm2', ifdSelectedCourse)
                        for (paramName, datarefName, ifdSimInterfaceModel) in radioModels:
                            freqChanged = False
                        else:
                            try:
                                prevValueXplane = prevValuesXplane[paramName]
                            except:
                                prevValueXplane = 0

                        try:
                            prevValue = prevValuesIfd[paramName]
                        except:
                            prevValue = 0
                        else:
                            try:
                                currentXplaneValueKhz = int(g_axPlane.params[paramName] * 10)
                            except:
                                currentXplaneValueKhz = 0
                            else:
                                if paramName != 'Nav2Freq':
                                    if currentXplaneValueKhz > 0:
                                        if currentXplaneValueKhz != prevValueXplane:
                                            if currentXplaneValueKhz != int(prevValue):
                                                with dllLock:
                                                    print('Xplane tuned radio {0}: {1}'.format(paramName, currentXplaneValueKhz))
                                                    g_SimInterface.set_sim_int('IfdRadio.' + ifdSimInterfaceModel, currentXplaneValueKhz)
                                                freqChanged = True
                                                prevValuesIfd[paramName] = currentXplaneValueKhz
                                            prevValuesXplane[paramName] = currentXplaneValueKhz
                                            with dllLock:
                                                currentValueKhz = g_SimInterface.get_sim_int('IfdRadio.' + ifdSimInterfaceModel)
                                                try:
                                                    prevValue = prevValuesIfd[paramName]
                                                except:
                                                    prevValue = 0
                                                else:
                                                    if int(currentValueKhz) != int(prevValue):
                                                        if prevValueXplane > 0:
                                                            freqChanged = True
                                                            print('Freq change detected {0} (new value: {1:.3f} MHz--old {2:.3f} MHz)'.format(paramName, currentValueKhz / 1000.0, prevValue / 1000.0))
                                                            g_axPlane.set_dataref('sim/cockpit2/radios/actuators/' + datarefName + '_hz', currentValueKhz / 10.0)
                                                        prevValuesIfd[paramName] = currentValueKhz
                                                        if paramName == 'Nav1ActiveFreq':
                                                            if freqChanged:
                                                                g_SimInterface.set_sim_string('IfdRadio.navId1', '')
                                                                g_axPlane.params['nav1_nav_id'] = ''
                                        if rateGroup1Hz:
                                            with dllLock:
                                                try:
                                                    navId = g_axPlane.params['nav1_nav_id']
                                                except KeyError:
                                                    print('VOR name not set')
                                                else:
                                                    status = g_SimInterface.set_sim_string('IfdRadio.navId1', navId)
                                        else:
                                            if rateGroup2Hz:
                                                with dllLock:
                                                    inVlocGuidance = g_SimInterface.get_sim_bool('IfdRadio.in_vloc_guidance')
                                                    inFmsGuidance = g_SimInterface.get_sim_bool('IfdRadio.in_fms_guidance')
                                                    inObsMode = g_SimInterface.get_sim_bool('IfdRadio.in_obs_mode')
                                                    try:
                                                        xplaneNavMode = int(g_axPlane.params['HsiSourceSelect'])
                                                    except KeyError:
                                                        pass
                                                    else:
                                                        xplaneModeDiffFromIfdMode = xplaneNavMode != prevIfdNavMode
                                                        if xplaneNavMode != prevXplaneNavMode:
                                                            if xplaneModeDiffFromIfdMode:
                                                                print('Mode: curr{0}, prev{1}, ifd{2}'.format(xplaneNavMode, prevXplaneNavMode, prevIfdNavMode))
                                                                xplaneGpsMode = xplaneNavMode == 2
                                                                if xplaneGpsMode:
                                                                    print('XPlane GPS mode')
                                                                    stat = g_SimInterface.set_sim_int('IfdRadio.nav_mode', 1)
                                                                    if not stat:
                                                                        print('failed to set mode', g_SimInterface.clear_last_error())
                                                                else:
                                                                    print('XPlane VHF mode')
                                                                    g_SimInterface.set_sim_int('IfdRadio.nav_mode', 0)
                                                                g_axPlane.set_dataref('sim/operation/override/override_gps', xplaneGpsMode)
                                                                g_axPlane.set_dataref('sim/operation/override/override_navneedles', xplaneGpsMode)
                                                            prevXplaneNavMode = xplaneNavMode
                                                            if inVlocGuidance != lastVlocGuidanceState:
                                                                modeStr = ''
                                                                modeStr += 'VLOC ' if inVlocGuidance else ''
                                                                modeStr += 'FMS ' if inFmsGuidance else ''
                                                                modeStr += '(OBS)' if inObsMode else ''
                                                                print('Guidance Mode has changed, now: {0}'.format(modeStr))
                                                                eNav1 = 0
                                                                eNav2 = 1
                                                                eGps = 2
                                                                navSource = eGps if inFmsGuidance else eNav1
                                                                prevIfdNavMode = navSource
                                                                g_axPlane.set_dataref('sim/cockpit2/radios/actuators/HSI_source_select_pilot', navSource)
                                                                g_axPlane.set_dataref('sim/cockpit2/radios/actuators/RMI_source_select_pilot', navSource)
                                                                g_axPlane.set_dataref('sim/operation/override/override_gps', inFmsGuidance)
                                                                g_axPlane.set_dataref('sim/operation/override/override_navneedles', inFmsGuidance)
                                                            lastVlocGuidanceState = inVlocGuidance
                                            if rateGroup10Hz:
                                                with dllLock:
                                                    inFmsGuidance = g_SimInterface.get_sim_bool('IfdRadio.in_fms_guidance')
                                                    if inFmsGuidance:
                                                        hdev = g_SimInterface.get_sim('IfdRadio.hdev')
                                                        vdev = -g_SimInterface.get_sim('IfdRadio.vdev')
                                                        if g_chassisId == 0:
                                                            g_axPlane.set_dataref('sim/cockpit/radios/gps_hdef_dot', hdev * 2.5 * 2)
                                                            g_axPlane.set_dataref('sim/cockpit/radios/gps_vdef_dot', vdev * 2.5 * 2)
                                                            g_axPlane.set_dataref('sim/cockpit/radios/nav1_hdef_dot', hdev * 2.5 * 2)
                                                            g_axPlane.set_dataref('sim/cockpit/radios/nav1_vdef_dot', vdev * 2.5 * 2)
                                                        else:
                                                            g_axPlane.set_dataref('sim/cockpit/radios/gps_hdef_dot2', hdev * 2.5 * 2)
                                                            g_axPlane.set_dataref('sim/cockpit/radios/gps_vdef_dot2', vdev * 2.5 * 2)
                                                            g_axPlane.set_dataref('sim/cockpit/radios/nav1_hdef_dot2', hdev * 2.5 * 2)
                                                            g_axPlane.set_dataref('sim/cockpit/radios/nav1_vdef_dot2', vdev * 2.5 * 2)
                                                        is_to_from_valid = g_SimInterface.get_sim_bool('IfdRadio.is_to_from_valid')
                                                        is_to = g_SimInterface.get_sim_bool('IfdRadio.is_to_from_to')
                                                        toFromFlag = 1 if is_to else 2
                                                        toFromFlag = toFromFlag if is_to_from_valid else 0
                                                        if g_chassisId == 0:
                                                            g_axPlane.set_dataref('sim/cockpit/radios/gps_fromto', toFromFlag)
                                                            g_axPlane.set_dataref('sim/cockpit/radios/nav1_fromto', toFromFlag)
                                                        else:
                                                            g_axPlane.set_dataref('sim/cockpit/radios/gps_fromto2', toFromFlag)
                                                            g_axPlane.set_dataref('sim/cockpit/radios/nav1_fromto2', toFromFlag)
                                                    if g_chassisId == 0:
                                                        hasGs = 1 if g_SimInterface.get_sim_bool('IfdRadio.is_main_vdev_valid') else 0
                                                        g_axPlane.set_dataref('sim/cockpit/radios/gps_has_glideslope', hasGs)
                                                        try:
                                                            tunedCrs = (g_axPlane.params['obsSelCourse'] + 360.0) % 360.0
                                                        except KeyError:
                                                            tunedCrs = 0.0
                                                        else:
                                                            g_SimInterface.set_sim('IfdRadio.vorSelCourse', tunedCrs)
                                            time.sleep(0.1)

                print('exiting IFD read thread')
            

            def Shutdown():
                global g_runningThreads
                global g_xavionReceiver
                global g_xavionRepeater
                print('Shutting down...')
                g_runningThreads = False
                try:
                    g_axPlane.disconnect()
                except:
                    pass
                else:
                    try:
                        g_xavionReceiver.stop()
                    except:
                        pass
                    else:
                        try:
                            g_xavionRepeater.stop()
                        except:
                            pass
                        else:
                            with dllLock:
                                try:
                                    g_SimInterface.Shutdown()
                                except:
                                    pass
            

            def cmdMain():
                parser = argparse.ArgumentParser()
                parser.add_argument('-i', '--ipAddr', help='Set Explicit Ip Address (and optional port after :)')
                parser.add_argument('-x', '--xplaneIpAddr', help='Set Explicit Ip Address (and optional port after :) for Xplane')
                parser.add_argument('-c', '--chassisId', default=0, help='Set IFD Chassis Id')
                parser.add_argument('--forceIfd', help='Force IFD mode instead of iPadMode', action='store_true')
                parser.add_argument('-e', '--enableOpt', help='Set Optional feature on', action='append')
                (args, unknownArgs) = parser.parse_known_args()
                if len(unknownArgs) > 0:
                    print('Some unrecognized command line arguments: {0}'.format(unknownArgs))
                if args.forceIfd:
                    print('forceIfd turned on')
                enabledOptions = ['ShadinFadc']
                if args.enableOpt:
                    enabledOptions = args.enableOpt
                    print('Optional features enabled: ', enabledOptions)
                print(args.chassisId)
                main(forceIfdMode=(args.forceIfd), ipAddr=(args.ipAddr), xpIpAndPort=(args.xplaneIpAddr), chassisId=(int(args.chassisId)), options=enabledOptions)
            

            def do_xavion_subscriptions():
                g_xavionReceiver.add_vetl_rx('sim/flightmodel/position/latitude', set_sim_param, freq=10, shortName='Gps.Latitude')
                g_xavionReceiver.add_vetl_rx('sim/flightmodel/position/longitude', set_sim_param, freq=10, shortName='Gps.Longitude')
                g_xavionReceiver.add_vetl_rx('sim/flightmodel/position/elevation', on_msl_elevation, freq=10, shortName='Gps.Altitude')
                g_xavionReceiver.add_vetl_rx('sim/flightmodel/position/local_vx', set_sim_param, freq=10, shortName='Gps.EVel')
                g_xavionReceiver.add_vetl_rx('sim/flightmodel/position/local_vy', set_sim_param, freq=10, shortName='Gps.VVel')
                g_xavionReceiver.add_vetl_rx('sim/flightmodel/position/local_vz', (ModifyDatum(set_sim_param, (lambda x: x * -1))), freq=10, shortName='Gps.NVel')
                g_xavionReceiver.add_vetl_rx('sim/cockpit2/gauges/indicators/pitch_AHARS_deg_pilot', (ModifyDatum(set_sim_param, (lambda x: math.radians(x) / 2))), freq=10, shortName='AHRS.Pitch')
                g_xavionReceiver.add_vetl_rx('sim/cockpit2/gauges/indicators/roll_AHARS_deg_pilot', (ModifyDatum(set_sim_param, (lambda x: math.radians(x)))), freq=10, shortName='AHRS.Roll')
                g_xavionReceiver.add_vetl_rx('sim/flightmodel/position/P', (ModifyDatum(set_sim_param, (lambda x: math.radians(x)))), freq=10, shortName='AHRS.RollRate')
                g_xavionReceiver.add_vetl_rx('sim/flightmodel/position/Q', (ModifyDatum(set_sim_param, (lambda x: math.radians(x)))), freq=10, shortName='AHRS.PitchRate')
                g_xavionReceiver.add_vetl_rx('sim/flightmodel/position/R', (ModifyDatum(set_sim_param_and_sync, (lambda x: math.radians(x)))), freq=10, shortName='AHRS.YawRate')
            

            def do_xavion_beta_subscriptions():
                for i in range(5):
                    i1 = i + 1
                    g_xavionReceiver.add_vetl_rx(('VeTOL_inverter_temp_{}A'.format(i1)), set_sim_param, freq=2, shortName=('AcSysData.inverterTemp{}A'.format(i)))
                    g_xavionReceiver.add_vetl_rx(('VeTOL_inverter_temp_{}B'.format(i1)), set_sim_param, freq=2, shortName=('AcSysData.inverterTemp{}B'.format(i)))
                    g_xavionReceiver.add_vetl_rx(('VeTOL_stator_temp_{}'.format(i1)), set_sim_param, freq=2, shortName=('AcSysData.statorTemp{}'.format(i)))
                    g_xavionReceiver.add_vetl_rx(('VeTOL_batt_temp_{}'.format(i1)), set_sim_param, freq=2, shortName=('AcSysData.batteryTemp{}'.format(i)))
            

            def main(forceIfdMode=False, ipAddr=None, xpIpAndPort=None, chassisId=0, options=[]):
                global g_SimInterface
                global g_axPlane
                global g_chassisId
                global g_xavionReceiver
                global g_xavionRepeater
                localAviLib = False
                runDir = os.getcwd()
                print('========================================')
                print('Version {0}\n\n'.format(get_version_str()))
                try:
                    g_SimInterface = SimApi.get_sim_interface_dll_api('../../IFD/Sim Protocol/Dist')
                    print('Loading AviLib (dynamic)')
                except:
                    g_SimInterface = SimApi.get_sim_interface_local('../../IFD/Sim Protocol')
                    print('Loading AviLib')
                    localAviLib = True
                else:
                    ipadMode = not forceIfdMode
                    if ipAddr is None:
                        if ipadMode:
                            ipAddr = ''
                        else:
                            if sys.version_info[0] < 3:
                                ipAddr = raw_input('Enter the IP Address of the IFD: ')
                            else:
                                ipAddr = input('Enter the IP Address of the IFD: ')
                            if ipAddr == ' ':
                                ipAddr = '10.0.4.128'
                            print('Ip Addr', ipAddr)
                    g_chassisId = chassisId
                    print('\n------------------------------------------------------------')
                    print('Ensure the IFD ARINC 429 is  configured as follows:')
                    print('\tPort    Speed    Data')
                    if 'Arinc429' in options:
                        print('\tIn 1    High     EFIS/Airdata')
                        print('\tIn 2    Low      Off')
                        print('\tOut 1   High     Arinc 429')
                        print('\tOut 2   Low      Off')
                    else:
                        print('\tIn 1    Low      Off')
                        print('\tIn 2    Low      Off')
                        print('\tOut 1   Low      Off')
                        print('\tOut 2   Low      Off')
                    print('\n')
                    print('\tSDI  Common')
                    print('\tVNAV  Disable Labels')
                    print('\n\n')
                    print('Ensure the IFD RS232 is  configured as follows:')
                    print('\tPort    Input                Output')
                    if 'BetaCan' in options:
                        print('\tCHNL 1  Beta Alia            Beta Alia')
                    else:
                        print('\tCHNL 1  Off                  Off')
                    if 'ShadinFadc' in options:
                        print('\tCHNL 2  Shadin-fadc          Off')
                    else:
                        print('\tCHNL 2  Off                  Off')
                    print('\tCHNL 3  CrossSync            CrossSync')
                    print('\tCHNL 4  Off                  Off')
                    print('\tCHNL 5  Off                  Off')
                    print('\tCHNL 6  Off                  Off')
                    print('------------------------------------------------------------\n')
                    g_SimInterface.SetChassisId(chassisId)
                for opt in options:
                    print('opt', opt)
                    g_SimInterface.SetOption(opt, True)
                else:
                    g_SimInterface.Start(ipAddr)
                    g_axPlane = AviXplaneUdp.AviXplaneUdp()
                    connected = g_axPlane.connect(xpIpAndPort)
                    try:
                        g_axPlane.block_rx_subscriptions_from_file('blocked_datarefs.dat')
                    except:
                        print('no blocked_datarefs.dat file found--allowing all dataref subscriptions')
                    else:
                        useXavion = False
                        useXavionBeta = 'BetaCan' in options
                        if useXavion or useXavionBeta:
                            g_xavionRepeater = XavionReceiver.start_xavion_repeat_server()
                            g_xavionReceiver = XavionReceiver.XavionThreadedReceiver(useRepeatServer=True)
                            g_xavionReceiver.start()
                        if connected:
                            if not useXavion:
                                g_axPlane.add_rx_subscription('sim/flightmodel/position/latitude', set_sim_param, freq=10, shortName='Gps.Latitude')
                                g_axPlane.add_rx_subscription('sim/flightmodel/position/longitude', set_sim_param, freq=10, shortName='Gps.Longitude')
                                g_axPlane.add_rx_subscription('sim/flightmodel/position/elevation', on_msl_elevation, freq=10, shortName='Gps.Altitude')
                                g_axPlane.add_rx_subscription('sim/flightmodel/position/local_vx', set_sim_param, freq=10, shortName='Gps.EVel')
                                g_axPlane.add_rx_subscription('sim/flightmodel/position/local_vy', set_sim_param, freq=10, shortName='Gps.VVel')
                                g_axPlane.add_rx_subscription('sim/flightmodel/position/local_vz', (ModifyDatum(set_sim_param, lambda x: x * -1)), freq=10, shortName='Gps.NVel')
                                g_axPlane.add_rx_subscription('sim/cockpit2/gauges/indicators/pitch_AHARS_deg_pilot', (ModifyDatum(set_sim_param, lambda x: math.radians(x))), freq=10, shortName='AHRS.Pitch')
                                g_axPlane.add_rx_subscription('sim/cockpit2/gauges/indicators/roll_AHARS_deg_pilot', (ModifyDatum(set_sim_param, lambda x: math.radians(x))), freq=10, shortName='AHRS.Roll')
                                xplaneTurnandSlipToTurnRate = 0.15789473684210525
                                g_axPlane.add_rx_subscription('sim/cockpit2/gauges/indicators/turn_rate_roll_deg_pilot', (ModifyDatum(set_sim_param, lambda x: math.radians(x * xplaneTurnandSlipToTurnRate))), freq=10, shortName='AHRS.HeadingRate')
                                g_axPlane.add_rx_subscription('sim/flightmodel/position/P', (ModifyDatum(set_sim_param, lambda x: math.radians(x))), freq=10, shortName='AHRS.RollRate')
                                g_axPlane.add_rx_subscription('sim/flightmodel/position/Q', (ModifyDatum(set_sim_param, lambda x: math.radians(x))), freq=10, shortName='AHRS.PitchRate')
                                g_axPlane.add_rx_subscription('sim/flightmodel/position/R', (ModifyDatum(set_sim_param_and_sync, lambda x: math.radians(x))), freq=10, shortName='AHRS.YawRate')
                            else:
                                do_xavion_subscriptions()
                            if 'BetaCan' in options:
                                g_axPlane.params['thrustReverser4Status'] = 0
                                g_axPlane.add_rx_subscription('sim/cockpit2/annunciators/reverser_on[4]', store_param, freq=4, shortName='thrustReverser4Status')
                                g_axPlane.add_rx_subscription('sim/flightmodel/engine/ENGN_thro_use[0]', (ModifyDatum(set_sim_param, lambda x: x * 2000)), freq=4, shortName='AcSysData.rpm0')
                                g_axPlane.add_rx_subscription('sim/flightmodel/engine/ENGN_thro_use[1]', (ModifyDatum(set_sim_param, lambda x: x * 2000)), freq=4, shortName='AcSysData.rpm1')
                                g_axPlane.add_rx_subscription('sim/flightmodel/engine/ENGN_thro_use[2]', (ModifyDatum(set_sim_param, lambda x: x * 2000)), freq=4, shortName='AcSysData.rpm2')
                                g_axPlane.add_rx_subscription('sim/flightmodel/engine/ENGN_thro_use[3]', (ModifyDatum(set_sim_param, lambda x: x * 2000)), freq=4, shortName='AcSysData.rpm3')
                                g_axPlane.add_rx_subscription('sim/flightmodel/engine/ENGN_thro_use[4]', (ModifyDatum(set_sim_param, lambda x: x * 2000 if int(g_axPlane.params['thrustReverser4Status']) == 0 else x * -2000)), freq=4, shortName='AcSysData.rpm4')
                                g_axPlane.add_rx_subscription('sim/flightmodel/engine/ENGN_TRQ[0]', (ModifyDatum(set_sim_param, lambda x: max(x, 0.0))), freq=4, shortName='AcSysData.torque0')
                                g_axPlane.add_rx_subscription('sim/flightmodel/engine/ENGN_TRQ[1]', (ModifyDatum(set_sim_param, lambda x: max(x, 0.0))), freq=4, shortName='AcSysData.torque1')
                                g_axPlane.add_rx_subscription('sim/flightmodel/engine/ENGN_TRQ[2]', (ModifyDatum(set_sim_param, lambda x: max(x, 0.0))), freq=4, shortName='AcSysData.torque2')
                                g_axPlane.add_rx_subscription('sim/flightmodel/engine/ENGN_TRQ[3]', (ModifyDatum(set_sim_param, lambda x: max(x, 0.0))), freq=4, shortName='AcSysData.torque3')
                                g_axPlane.add_rx_subscription('sim/flightmodel/engine/ENGN_TRQ[4]', set_sim_param, freq=4, shortName='AcSysData.torque4')
                                g_axPlane.add_rx_subscription('sim/flightmodel/controls/elv_trim', (ModifyDatum(set_sim_param, lambda x: x * -100)), freq=2, shortName='AcSysData.pitchTrim')
                                g_axPlane.add_rx_subscription('sim/flightmodel/controls/ail_trim', (ModifyDatum(set_sim_param, lambda x: x * 100)), freq=2, shortName='AcSysData.rollTrim')
                                g_axPlane.add_rx_subscription('sim/flightmodel/controls/rud_trim', (ModifyDatum(set_sim_param, lambda x: x * 100)), freq=2, shortName='AcSysData.yawTrim')
                                g_axPlane.params['inceptor_pitch'] = -100
                                g_axPlane.params['inceptor_roll'] = -100
                                g_axPlane.params['inceptor_yaw'] = -100
                                g_axPlane.params['inceptor_hover'] = 0
                                g_axPlane.params['inceptor_pusher'] = 0
                                g_axPlane.add_rx_subscription('BETA/dref_can_pitch', (ModifyDatum(store_param, lambda x: (x - 0.5) * 200)), freq=4, shortName='inceptor_pitch')
                                g_axPlane.add_rx_subscription('BETA/dref_can_roll', (ModifyDatum(store_param, lambda x: (x - 0.5) * 200)), freq=4, shortName='inceptor_roll')
                                g_axPlane.add_rx_subscription('BETA/dref_can_yaw', (ModifyDatum(store_param, lambda x: (x - 0.5) * 200)), freq=4, shortName='inceptor_yaw')
                                g_axPlane.params['using_inceptor_can'] = False

                                def using_inceptor_input():
                                    g_axPlane.params['using_inceptor_can'] = g_axPlane.params['using_inceptor_can'] or g_axPlane.params['inceptor_pitch'] != -100 or g_axPlane.params['inceptor_roll'] != -100 or g_axPlane.params['inceptor_yaw'] != -100
                                    return g_axPlane.params['using_inceptor_can']

                                g_axPlane.add_rx_subscription('sim/cockpit2/controls/total_pitch_ratio', (ModifyDatum(set_sim_param, lambda x: g_axPlane.params['inceptor_pitch'] if using_inceptor_input() else x * -100)), freq=4, shortName='AcSysData.pitchCmd')
                                g_axPlane.add_rx_subscription('sim/cockpit2/controls/total_roll_ratio', (ModifyDatum(set_sim_param, lambda x: g_axPlane.params['inceptor_roll'] if using_inceptor_input() else x * 100)), freq=4, shortName='AcSysData.rollCmd')
                                g_axPlane.add_rx_subscription('sim/cockpit2/controls/total_heading_ratio', (ModifyDatum(set_sim_param, lambda x: g_axPlane.params['inceptor_yaw'] if using_inceptor_input() else x * 100)), freq=4, shortName='AcSysData.yawCmd')
                                g_axPlane.add_rx_subscription('sim/cockpit2/electrical/bus_volts[0]', set_sim_param, freq=4, shortName='AcSysData.volts0')
                                g_axPlane.add_rx_subscription('sim/cockpit2/electrical/bus_load_amps[0]', set_sim_param, freq=4, shortName='AcSysData.amps0')
                                do_xavion_beta_subscriptions()
                                for i in range(0, 5):
                                    batteryTotalCapacity = 105000
                                    thisBatteryFudge = [0.8,1.2,1.0,1.1,0.9]
                                    g_axPlane.add_rx_subscription(('sim/cockpit/electrical/battery_charge_watt_hr[{}]'.format(i)), (ModifyDatum(set_sim_param, lambda x, i=i: min(100.0, 100.0 * x / batteryTotalCapacity))), freq=1, shortName=('AcSysData.batterySoc{}'.format(i)))
                                else:
                                    g_axPlane.add_rx_subscription('sim/flightmodel/position/local_ax', set_sim_param, freq=10, shortName='AHRS.Latitudinal_Acceleration')
                                    g_axPlane.add_rx_subscription('sim/flightmodel/position/local_ay', set_sim_param, freq=10, shortName='AHRS.Longitudinal_Acceleration')
                                    g_axPlane.add_rx_subscription('sim/flightmodel/position/local_az', (ModifyDatum(set_sim_param, lambda x: x - 9.8)), freq=10, shortName='AHRS.Normal_Acceleration')
                                    g_axPlane.add_rx_subscription('sim/cockpit2/gauges/indicators/heading_AHARS_deg_mag_pilot', (ModifyDatum(set_sim_param, lambda x: deg_pi(math.radians(x)))), freq=10, shortName='AHRS.Heading')
                                    g_axPlane.add_rx_subscription('sim/cockpit2/gauges/indicators/sideslip_degrees', (ModifyDatum(set_sim_param, lambda x: math.sin(math.radians(x)) * -9.8)), freq=5, shortName='AHRS.SlipSkid')
                                    g_axPlane.params['nav1_fromto'] = 0
                                    g_axPlane.params['nav1_gsvalid'] = 0
                                    g_axPlane.add_rx_subscription('sim/cockpit/radios/nav1_fromto', store_param, freq=2, shortName='nav1_fromto')
                                    g_axPlane.add_rx_subscription('sim/cockpit/radios/nav1_CDI', store_param, freq=2, shortName='nav1_gsvalid')
                                    g_axPlane.add_rx_subscription('sim/cockpit/radios/nav1_hdef_dot', (ModifyDatum(set_sim_param, lambda x: x / 2.0 if g_axPlane.params['nav1_fromto'] > 0 else -999)), freq=10, shortName='IfdRadio.loc_hdev')
                                    g_axPlane.add_rx_subscription('sim/cockpit/radios/nav1_vdef_dot', (ModifyDatum(set_sim_param, lambda x: -x / 2.0 if g_axPlane.params['nav1_fromto'] > 0 else -999)), freq=10, shortName='IfdRadio.gs_vdev')
                                    g_axPlane.add_rx_subscription('sim/cockpit/radios/nav1_course_degm', store_param, freq=2, shortName='obsSelCourse')
                                    g_axPlane.params['obsSelCourse'] = 0.0
                                    g_axPlane.add_rx_subscription('sim/cockpit/radios/nav1_hdef_dot', (ModifyDatum(set_sim_param, lambda x: (360 + g_axPlane.params['obsSelCourse'] - x / 2.0 * 10.0) % 360)), freq=10, shortName='IfdRadio.vorRadial')
                                    g_axPlane.params['xplaneApGpssMode'] = 0
                                    g_axPlane.params['xplaneApApproachStatus'] = 0
                                    g_axPlane.add_rx_subscription('sim/cockpit2/autopilot/gpss_status', store_param, freq=2, shortName='xplaneApGpssMode')
                                    g_axPlane.add_rx_subscription('sim/cockpit2/autopilot/approach_status', store_param, freq=2, shortName='xplaneApApproachStatus')
                                    g_axPlane.add_rx_subscription('sim/cockpit2/gauges/indicators/heading_AHARS_deg_mag_pilot', (ModifyDatum(set_sim_param, lambda x: deg_360(x))), freq=10, shortName='Airdata.Hdg')
                                    g_axPlane.add_rx_subscription('sim/cockpit2/gauges/indicators/true_airspeed_kts_pilot', set_sim_param, freq=5, shortName='Airdata.TAS')
                                    g_axPlane.add_rx_subscription('sim/cockpit2/gauges/indicators/airspeed_kts_pilot', set_sim_param, freq=16, shortName='Airdata.IAS')
                                    g_axPlane.add_rx_subscription('sim/cockpit2/gauges/indicators/altitude_ft_pilot', set_sim_param, freq=8, shortName='Airdata.Hc')
                                    g_axPlane.add_rx_subscription('sim/flightmodel2/misc/AoA_angle_degrees', set_sim_param, freq=4, shortName='Airdata.AoA')
                                    g_axPlane.add_rx_subscription('sim/flightmodel/position/vh_ind', set_sim_param, freq=5, shortName='Airdata.VSpeed')
                                    g_axPlane.add_rx_subscription('sim/cockpit2/gauges/actuators/barometer_setting_in_hg_pilot', set_sim_param, freq=2, shortName='Airdata.BaroSetting')
                                    g_axPlane.add_rx_subscription('sim/weather/temperature_ambient_c', set_sim_param, freq=1, shortName='Airdata.SAT')
                                    g_axPlane.add_rx_subscription('sim/weather/temperature_le_c', set_sim_param, freq=1, shortName='Airdata.OAT')
                                    vorStrNames = [
                                     'first','second','third','fourth','fifth','sixth']
                                    for i in range(5):
                                        g_axPlane.add_rx_subscription(('sim/cockpit2/radios/indicators/nav1_nav_id[{0}]'.format(i)), store_string_param, freq=1.0, shortName=('nav1_nav_id[{0}]'.format(i)))
                                    else:
                                        for paramName, datarefName, ifdSimInterfaceModel in radioModels:
                                            g_axPlane.add_rx_subscription(('sim/cockpit2/radios/actuators/{0}_hz'.format(datarefName)), store_param, freq=1.0, shortName=paramName)
                                        else:
                                            g_axPlane.add_rx_subscription('sim/cockpit2/radios/actuators/HSI_source_select_pilot', store_param, freq=2.0, shortName='HsiSourceSelect')
                                            readFromIfdThread = threading.Thread(target=read_from_ifd_thread)
                                            readFromIfdThread.start()
                                            try:
                                                try:
                                                    while True:
                                                        if g_runningThreads:
                                                            if not g_SimInterface.IsRunning():
                                                                print('Sim Interface connection failure')
                                                                Shutdown()
                                                                raise Exception('Exiting')
                                                            try:
                                                                g_axPlane.rx_data()
                                                                with dllLock:
                                                                    g_SimInterface.set_sim('AHRS.SplatFlags_Outright', 0.0)
                                                                    g_SimInterface.set_sim('AHRS.Flags_Outright', 1.0)
                                                            except KeyboardInterrupt:
                                                                Shutdown()
                                                                exit()
                                                            except XPlaneUdp.XPlaneTimeout:
                                                                print('Timeout waiting for XPlane')
                                                                time.sleep(0.5)

                                                except Exception as e:
                                                    try:
                                                        print(e)
                                                    finally:
                                                        e = None
                                                        del e

                                            finally:
                                                LookupError()
                                                time.sleep(1.0)


            if __name__ == '__main__':
                cmdMain()