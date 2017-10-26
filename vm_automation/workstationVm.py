import subprocess
import os
import time

vmrunExe = "C:\\Program Files (x86)\\VMware\\VMware Workstation\\vmrun.exe"
vmPath = "D:\\VMs"

class workstationServer:
    def __init__(self, vmRunExe, vmPath, logFile = "default.log"):
        self.vmrunExe = vmRunExe
        self.vmPath = vmPath
        self.vmList = []
        return None

    def __init__(self, configDictionary, logFile = "default.log"):
        try:
            self.vmrunExe =     configDictionary['VMRUN_PATH']
            self.vmPath =       configDictionary['VM_PATH']
        except:
            return None
        self.vmList = []
        return None
    
    def enumerateVms(self, negFilter = None):
        for root, dirs, files in os.walk(vmPath):
            for file in files:
                if file.endswith(".vmx"):
                    if negFilter != None and negFilter.upper() in root.upper():
                        continue
                    else:
                        self.vmList.append(workstationVm(os.path.join(root, file)))
        return True
    
    def waitForVmsToBoot(self, vmList):
        # apt_shared.logMsg("WAITING FOR VMS TO BE READY; THIS COULD TAKE A FEW MINUTES")
        readyVms = []
        ipAddressesSet = False
        while not ipAddressesSet:
            ipAddressesSet = True
            for i in vmList:
                if i not in readyVms:
                    if i.queryVmIp():
                        # apt_shared.logMsg(i.vmName + " READY; IP = " + i.getVmIp())
                        readyVms.append(i)
                    else:
                        ipAddressesSet = False
                time.sleep(1)
        # apt_shared.logMsg("VMS APPEAR TO BE READY; PULLING IP ADDRESSES TO VERIFY")
        # for i in vmList:
            # apt_shared.logMsg("IP ADDRESS FOR " + i.vmName + " = " + i.getVmIp())
        return True
    
class workstationVm:
    
    def __init__(self, vmIdentifier):
        self.procList = []
        self.revertSnapshots = []
        self.snapshotList = []
        self.testVm = False
        self.vmIdentifier = vmIdentifier
        self.vmIp = ""
        self.vmName = vmIdentifier.split('\\')[-1][:-4]
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
        vmRunCmd = [vmrunExe] + listCmd
        vmrunProc = subprocess.Popen(vmRunCmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return vmrunProc.communicate()
    
    def runAuthenticatedVmCommand(self, listCmd):
        vmRunCmd = [vmrunExe] + ['-gu', self.vmUsername, '-gp', self.vmPassword] + listCmd
        vmrunProc = subprocess.Popen(vmRunCmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return vmrunProc.communicate()
    
    def deleteSnapshot(self, snapshotName):
        return self.runVmCommand(['deleteSnapshot', self.vmIdentifier, snapshotName])
    
    def getArch(self):
        return self.arch

    def getFileFromGuest(self, srcPathName, dstPathName):
        return self.runAuthenticatedVmCommand(['CopyFileFromGuestToHost', self.vmIdentifier, srcPathName, dstPathName])        

    def getSnapshots(self):
        # apt_shared.logMsg("FINDING SNAPSHOTS FOR " + self.vmName)
        self.snapshotList = self.runVmCommand(['listSnapshots', self.vmIdentifier])[0].split('\n')
        # strip off newlines
        self.snapshotList = map(lambda s: s.strip(), self.snapshotList)
        return len(self.snapshotList)
            
    def getVmIp(self):
        return self.vmIp

    def getUsername(self):
        return self.vmUsername
    
    def isTestVm(self):
        return self.testVm
    
    def makeDirOnGuest(self, dirPath):
        return self.runAuthenticatedVmCommand(['createDirectoryInGuest', self.vmIdentifier, dirPath])
    
    def powerOn(self):
        self.runVmCommand(['start', self.vmIdentifier])
    
    def prepVm(self):
        # apt_shared.logMsg("PREPARING " + self.vmName + " FOR TESTING")
        # apt_shared.logMsg(self.vmName + " ARCHITECTURE: " + str(self.getArch()))
        self.getSnapshots()
        self.powerOn()
    
    def queryVmIp(self):
        tempIp = self.runVmCommand(['getGuestIPAddress', self.vmIdentifier])[0].strip()
        if 'error' in tempIp.lower():
            retVal = False
        else:
            self.vmIp = tempIp
            retVal = True
        return retVal
        
    def revertToSnapshot(self, snapshot):
        return self.runVmCommand(['revertToSnapshot', self.vmIdentifier, snapshot])[0]
    
    def revertDevVm(self):
        self.getSnapshots()
        for i in self.snapshotList:
            if "TESTING-" in i:
                self.revertToSnapshot(i)
                self.deleteSnapshot(i)
    
    def revertToTestingBase(self):
        self.getSnapshots()
        for i in self.snapshotList:
            if 'testing_base' in i.lower():
                return self.revertToSnapshot(i)
        return "NO SUCH SNAPSHOT"
    
    def runCmdOnGuest(self, argList):
        # apt_shared.logMsg("RUNNING '" + ' '.join(argList) + "' ON " + self.vmName)
        cmdRet = self.runAuthenticatedVmCommand(['runProgramInGuest', self.vmIdentifier] + argList)
        retVal = False
        if ('', '') == cmdRet:
            # apt_shared.logMsg(' '.join(argList) + "' ON " + self.vmName + " COMPLETED SUCCESSFULLY")
            retVal = True
        # else:
        #     apt_shared.logMsg(' '.join(argList) + "' ON " + self.vmName + " FAILED TO RUN: " + str(cmdRet))
        return retVal
    
    def setPassword(self, vmPassword):
        self.vmPassword = vmPassword

    def setTestVm(self):
        self.testVm = True
        
    def setUsername(self, vmUsername):
        self.vmUsername = vmUsername
    
    def takeTempSnapshot(self):
        snapshotName = "PAYLOAD_TESTING-" + str(time.time()).split('.')[0]
        self.runVmCommand(['snapshot', self.vmIdentifier, snapshotName])
        self.revertSnapshots.append(snapshotName)
        return snapshotName
        
    def updateProcList(self):
        self.procList = self.runAuthenticatedVmCommand(['listProcessesInGuest', self.vmIdentifier])[0].split('\n')
        return len(self.procList)

    def uploadFileToGuest(self, srcPathName, dstPathName):
        # apt_shared.logMsg("ATTEMPTING TO UPLOAD " + srcPathName)
        return self.runAuthenticatedVmCommand(['CopyFileFromHostToGuest', self.vmIdentifier, srcPathName, dstPathName])