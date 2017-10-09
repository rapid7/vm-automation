import virtualbox
import datetime

class virtualboxServer:
    """
    THE virtualboxServer CLASS IS A CLASS THAT STORES INFORMATION ON AND SIMPLIFIES INTERACTION
    WITH A VIRTUALBOX INSTANCE.
    """
    def __init__(self, logFile = "default.log"):
        self.logFile    = logFile
        self.vm         = virtualbox.VirtualBox()
        self.vmList     = []
        return None

    def enumerateVms(self, negFilter = None):
        for vm in self.vm.machines:
            if negFilter != None and negFilter.upper() in vm:
                continue
            else:
                self.vmList.append(virtualboxVm(self, vm))
        return True

    def waitForVmsToBoot(self, vmList):
        raise NotImplementedError

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
    """
    THE virtualboxVm CLASS IS A CLASS THAT STORES INFORMATION ON AND SIMPLIFIES INTERACTION
    WITH A VIRTUALBOX VM.
    """
    def __init__(self, serverObject, vmObject):
        self.server = serverObject
        self.vmObject = vmObject
        self.vmSession = None
        self.vmSessionGuest = None
        self.vmSessionGuestConsole = None
        self.procList = []
        self.revertSnapshots = []
        self.snapshotList = []
        self.testVm = False
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

    def runVmCommand(self, listCmd):
        raise NotImplementedError

    def runAuthenticatedVmCommand(self, listCmd):
        if not self.vmSessionGuest:
            self.vmSessionGuest = self.vmObject.create_session()
        if self.vmSessionGuest:
            if not self.vmSessionGuestConsole:
              self.vmSessionGuestConsole = self.vmSessionGuest.console.guest.create_session(self.vmUsername, self.vmPassword)
            if self.vmSessionGuestConsole:
              process, stdout, stderr = self.vmSessionGuestConsole.execute(listCmd[0], listCmd[1:])
              return stdout, stderr
        return False

    def deleteSnapshot(self, snapshotName):
        raise NotImplementedError

    def getArch(self):
        return self.arch

    def getFileFromGuest(self, srcPathName, dstPathName):
        raise NotImplementedError

    def getSnapshots(self):
        raise NotImplementedError

    def getVmIp(self):
        return self.vmIp

    def getUsername(self):
        return self.vmUsername

    def isTestVm(self):
        return self.testVm

    def isPoweredOff(self):
        return not self.isPoweredOn()

    def isPoweredOn(self):
        if self.vmObject.state >= virtualbox.library.MachineState.running:
            return True
        else:
            return False

    def makeDirOnGuest(self, dirPath):
        raise NotImplementedError

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
                self.vmSessionGuestConsole = None
                self.vmSessionGuest = None
                self.vmSession = None
            return

    def prepVm(self):
        raise NotImplementedError

    def queryVmIp(self):
        raise NotImplementedError

    def revertToSnapshot(self, snapshot):
        raise NotImplementedError

    def revertDevVm(self):
        raise NotImplementedError

    def revertToTestingBase(self):
        raise NotImplementedError

    def runCmdOnGuest(self, argList):
        cmdRet = self.runAuthenticatedVmCommand(argList)
        if cmdRet == ('', ''):
            return True
        return False

    def setPassword(self, vmPassword):
        self.vmPassword = vmPassword

    def setTestVm(self):
        self.testVm = True

    def setUsername(self, vmUsername):
        self.vmUsername = vmUsername

    def takeTempSnapshot(self):
        raise NotImplementedError

    def updateProcList(self):
        raise NotImplementedError

    def uploadFileToGuest(self, srcPathName, dstPathName):
        raise NotImplementedError
