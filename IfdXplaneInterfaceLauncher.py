import socket
import os
import subprocess
import sys
import time
import signal
import shlex

class Capabilites:

    def __init__(self, chassisIdDict):
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.chassisIds = chassisIdDict
        self.capPort = 5679
        self.bufferSize = 1024
        self.ipString = ""
        self.chassisID = None
        self.packet = None
        self.address = None

    def listen(self):

        try:
            self.listenSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listenSocket.settimeout(1.0)
            self.listenSocket.bind(('', self.capPort))

            while True:
                    try:
                        self.packet, (self.address, self.rxPort) = self.listenSocket.recvfrom(self.bufferSize)
                    except socket.timeout:
                        pass
                    else:
                        # fail safe
                        if len(self.packet) >= 32:

                            self.decodeChassis()
                            self.decodeIp()

                            if int(self.chassisID) < 2:
                                if self.address == self.ipString: #self.ipString.startswith('10.0.4'):
                                    if self.chassisID in self.chassisIds.keys():
                                        #we have already started the subprocess,
                                        #need to check if the process is still running
                                        procExitCode = self.chassisIds[self.chassisID].poll()
                                        if procExitCode is not None:
                                            #poll returns None as long as the subprocess is running
                                            print('Attempting to Restart subprocess; lastExitCode: {0}'.format(procExitCode))
                                            self.listenSocket.close()
                                            return self.ipString, self.chassisID
                                    else:
                                        self.decodeIp()
                                        self.listenSocket.close()
                                        return self.ipString, self.chassisID
                                else:
                                    print('Bad Address: Advertised {0} from {1}'.format(self.ipString, self.address))
                            else:
                                print('Bad Chassis ID: {0} from {1}'.format(self.chassisID, self.address))

        except:
            raise
        finally:
            #print('Closing Socket')
            try:
                self.listenSocket.close()
            except:
                print('Unable to close socket')


    def decodeIp(self):
        self.ipString = ''
        ipAddr = self.packet[1:5]
        for i in ipAddr:
            try:
                dec = int(hex(ord(i)), 16)
            except:
                dec = int(i)
            self.ipString += str(dec) + "."
        self.ipString = self.ipString[:-1]

    def decodeChassis(self):
        id = self.packet[13]
        try:
            self.chassisID = str(int(hex(ord(id)), 16))
        except:
            self.chassisID = str(int(id))

def main():
    print('Waiting for IFDs...')
    chassisIdDict = {}
    try:
        while True: #use ctrl-c to exit
            capabilitesListener = Capabilites(chassisIdDict)
            ip, chassis = capabilitesListener.listen()
            print('Starting connection to {0}, chassisId: {1}'.format(ip, chassis))
##            print('Use Ctrl-C from this window to close all connections')

            #CREATE_NEW_PROCESS_GROUP = 0x00000200
            DETACHED_PROCESS = 0x00000008

            #try to open the python version first
            if os.path.exists('AviXplaneInterface.py'):
                print("py -2 AviXplaneInterface.py --forceIfd -i {0} -c {1}".format(ip, chassis))
                newProcess = subprocess.Popen("py -2 AviXplaneInterface.py --forceIfd -i {0} -c {1} -e Arinc429  -e ShadinFadc".format(ip, chassis), shell=True, creationflags=8)
            else:
                newProcess = subprocess.Popen("AviXplaneInterface.exe --forceIfd -i {0} -c {1} -e Arinc429 -e ShadinFadc".format(ip, chassis), shell=True, creationflags=DETACHED_PROCESS)

##            SW_SHOW = 5
##            info = subprocess.STARTUPINFO()
##            info.dwFlags = subprocess.STARTF_USESHOWWINDOW
##            info.wShowWindow = SW_SHOW
##            newProcess = subprocess.Popen(shlex.split("AviXplaneInterface.exe --forceIfd -i {0} -c {1}".format(ip, chassis)), shell=False, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, startupinfo=info) #(DETACHED_PROCESS| subprocess.CREATE_NEW_PROCESS_GROUP))

            #newProcess = subprocess.Popen(shlex.split("AviXplaneInterface.exe --forceIfd -i {0} -c {1}".format(ip, chassis)), shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE) #(DETACHED_PROCESS| subprocess.CREATE_NEW_PROCESS_GROUP))
            procExitStatus = newProcess.poll()
            if(procExitStatus is not None):
                print('\tFailed to start interface, exit code {0}'.format(procExitStatus))
            else:
                print('\tStarted as PID: {0}'.format(newProcess.pid))



            chassisIdDict[chassis] = newProcess
    except KeyboardInterrupt:
        pass #normal exit
    finally:
        #time to clean up
        print('Exiting...')
        print('Make sure to close all Xplane Interface Processes before re-running.')
        time.sleep(5)
##        for chassis, proc in chassisIdDict.items():
##            print('Checking process: {0} (chassis {1})...'.format(proc.pid, chassis))
##            if proc.poll() is None:   #still runnning
##                print('Killing {0}'.format(proc.pid))
                #kill_proc_tree(proc.pid)
                #subprocess.Popen("TASKKILL /F /PID {} /T".format(proc.pid))
                #subprocess.Popen("TASKKILL /PID {} /T".format(proc.pid))
##                proc.terminate()
##                proc.kill()

if __name__ == '__main__':
    main()
