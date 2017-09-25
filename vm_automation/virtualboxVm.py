import virtualbox
import datetime

class virtualboxServer:
    """
    THE virtualboxServer CLASS IS A CLASS THAT STORES INFORMATION ON AND SIMPLIFIES INTERACTION
    WITH A VIRTUALBOX SERVER.
    """
    def __init__(self, hostname = "localhost", logFile = "defaultLogfile.log"):
        self.hostname   = hostname
        self.type       = "VirtualBox"
        self.logFile    = logFile
        self.fullName   = ""
        self.vm         = virtualbox.VirtualBox()
        self.vmList     = []

    def enumerateVms(self, negFilter = None):
        for vm in self.vm.machines:
            if negFilter != None and negFilter.upper() in vm:
                continue
            else:
                self.vmList.append(virtualboxVm(self, vm))

    def logMsg(self, strMsg):
                if strMsg == None:
                        strMsg="[None]"
                dateStamp = 'serverlog:[' + str(datetime.datetime.now())+ '] '
                #DELETE THIS LATER:
                print dateStamp + strMsg
                try:
                        logFileObj = open(self.logFile, 'ab')
                        logFileObj.write(dateStamp + strMsg + '\n')
                        logFileObj.close()
                except IOError:
                        return False
                return True

class virtualboxVm:
    def __init__(self, serverObject, vmObject):
        self.server = serverObject
        self.vmObject = vmObject
        self.vmSession = None
        self.procList = []
        self.revertSnapshots = []
        self.snapshotList = []
        self.testVm = False
        #self.vmIdentifier = vmIdentifier
        self.vmIp = ""
        self.vmName = str(self.vmObject.name)
        self.vmOS = self.vmName
        self.vmPassword = ""
        self.vmUsername = ""
        self.payloadList = []
        if 'x64' in self.vmName:
            self.arch = 'x64'
        elif 'x86' in self.vmName:
            self.arch = 'x86'
        else:
            self.arch = None

    def isPoweredOff(self):
        return not self.isPoweredOn()

    def isPoweredOn(self):
        if self.vmObject.state >= virtualbox.library.MachineState.running:
            return True
        else:
            return False

    def powerOn(self, asyncFlag = False):
        if self.isPoweredOn():
            self.server.logMsg(self.vmName + " IS ALREADY RUNNING, CANNOT POWER-ON HARDER")
            return None
        else:
            self.server.logMsg("POWERING ON " + self.vmName)
            self.vmSession = virtualbox.Session()
            process = self.vmObject.launch_vm_process(self.vmSession, "headless", "")
            if asyncFlag:
                process.wait_for_completion(5000)
            return

    def powerOff(self):
        if self.isPoweredOff():
            self.server.logMsg(self.vmName + " IS ALREADY OFF, CANNOT POWER-OFF HARDER")
            return None
        else:
            self.server.logMsg("POWERING OFF " + self.vmName)
            if self.vmSession:
                self.vmSession.console.power_down()
                self.vmSession.unlock_machine()
                self.vmSession = None
            return
