import argparse
import tempfile
import vm_automation
import sampleLib
import time
import os

def updateHostname(vm, hostname):
    # Remember machine state and ensure powered on
    powerState = vm.isPoweredOn()
    if powerState == False:
        vm.powerOn()
        startCount = 5
        while vm.checkTools() != 'TOOLS_READY' and startCount > 0:
            time.sleep(5)
            startCount -= 1

    # File creation for uploading
    fPoint,fPath = tempfile.mkstemp()
    cmdStr = None
    cmdArg = None

    # Windows path
    if ("Windows" in vm.vmOS):
        cmdStr = "wmic computersystem where name=\'%COMPUTERNAME%\' rename " + hostname + "\n"
        cmdArg = ["del", "C:\\windows\\temp\\updateHost.bat"]
    # Linux path
    else:
        cmdStr =  "#!/bin/sh -x\n"
        cmdStr += "HOSTNAME=`hostname`\n"
        cmdStr += "sed \'s/\'\"$HOSTNAME\"\'/" + hostname + "/g\' /etc/hosts > /tmp/hosts.new\n"
        cmdStr += "sed \'s/\'\"$HOSTNAME\"\'/" + hostname + "/g\' /etc/hostname > /tmp/hostname.new\n"
        cmdStr += "sudo mv /tmp/hosts.new /etc/hosts\n"
        cmdStr += "sudo mv /tmp/hostname.new /etc/hostname\n"
        cmdArg = ["rm", "/tmp/updateHost.sh"]
    # Write changes and run
    os.write(fPoint, cmdStr)
    os.close(fPoint)
    vm.uploadAndRun(fPath, cmdArg[1])
    vm.runCmdOnGuest(cmdArg)
    os.remove(fPath)

    # Power off VM for changes to persist
    if vm.checkTools() == 'TOOLS_READY' and vm.isPoweredOn():
        vm.vmObject.ShutdownGuest()
    else:
        vm.powerOff()
    # Wait
    while vm.isPoweredOn():
        time.sleep(5)
    # Return machine to original state
    if powerState != False:
        vm.powerOn()

    
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--keyword", help="VM search parameter")
    parser.add_argument("-cf", "--credsFile", help="credentials file for logging into the vm")
    parser.add_argument("-un", "--username", help="vm username")
    parser.add_argument("-pw", "--password", help="vm password")
    parser.add_argument("-n", "--hostname", help="New hostname for the VM")
    parser.add_argument("hypervisorConfig", help="json hypervisor config")
    
    args = parser.parse_args()

    hypervisorDic = {}
    vmServer = vm_automation.esxiServer.createFromFile(args.hypervisorConfig, './snapshot.log')

    """
    CHECK THAT WE HAVE REQUIRED CREDS SOMEHOW
    """
    if (args.username == None or args.password == None) and args.credsFile == None:
        print("VM CREDENTIALS REQUIRED FOR THIS OPERATION")
        exit(0)

    credsDictionary = None
    if args.credsFile is not None:
        credsDictionary = sampleLib.loadJsonFile(args.credsFile)
        if credsDictionary is None:
            print("FAILED TO LOAD CREDS FILE")
            exit(0)

    if vmServer != None:
        vmsToChange = sampleLib.makeVmList(vmServer, args.keyword, None)
        for vm in vmsToChange:
            vm_user = args.username
            vm_pass = args.password
            if credsDictionary is not None:
                for machine in credsDictionary:
                    if credsDictionary[machine]['NAME'] == vm.vmName:
                        vm_user = credsDictionary[machine]['USERNAME']
                        vm_pass = credsDictionary[machine]['PASSWORD']

            vm.setUsername(vm_user)
            vm.setPassword(vm_pass)

            updateHostname(vm, args.hostname)
            print("hostname changed for " + vm.vmName)


    
if __name__ == "__main__":
    main()
