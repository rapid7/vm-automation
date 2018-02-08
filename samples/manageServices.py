import argparse
import vm_automation
import multiprocessing
import os
import time
from pyVmomi import vim
import sampleLib
from Crypto.SelfTest.Random.test__UserFriendlyRNG import multiprocessing

def listCommands(commandDictionary):
        for key, value in commandDictionary.iteritems():
            print(key)
        return 1

def replaceUsername(actionData, username):
    if actionData['TYPE'] == 'COMMANDS':
        for i in range(len(actionData['COMMANDS'])):
            for j in range(len(actionData['COMMANDS'][i])):
                while 'VM_USERNAME' in actionData['COMMANDS'][i][j]:
                    actionData['COMMANDS'][i][j] = actionData['COMMANDS'][i][j].replace("VM_USERNAME", username)
                    
def replacePassword(actionData, password):
    if actionData['TYPE'] == 'COMMANDS':
        for i in range(len(actionData['COMMANDS'])):
            for j in range(len(actionData['COMMANDS'][i])):
                while 'VM_PASSWORD' in actionData['COMMANDS'][i][j]:
                    actionData['COMMANDS'][i][j] = actionData['COMMANDS'][i][j].replace("VM_PASSWORD", password)

def runCommands(vmObject, actionData):
    for command in actionData['COMMANDS']:
        for i in range(5):
            retVal = True
            try:
                if vmObject.runCmdOnGuest(command) == False:
                    retVal = False
            except vim.fault.InvalidState:
                retVal = False
                continue
            break
    return retVal

def runScript(vmObject, actionData):
    localScriptName = actionData['FILENAME']
    interpreter = actionData['INTERPRETER']
    remoteScriptName = actionData['UPLOAD_DIR'] + "\\" + localScriptName.split('/')[-1]
    retVal = False
    try:
        retVal = vmObject.uploadAndRun(localScriptName, remoteScriptName, interpreter, True)
    except Exception as e:
        print("CAUGHT EXCEPTION: " + str(e))
        retVal = False
    return retVal

def checkSuccess(vmObject, actionData):
    if 'SUCCESS_TYPE' in actionData and 'SUCCESS_METRIC' in actionData:
        if actionData['SUCCESS_TYPE'] == 'PROCESS':
            retVal = sampleLib.checkForProcess(vmObject, actionData['SUCCESS_METRIC'])
    else:
        print("NO SUCCESS_TYPE OR SUCCESS METRIC IN THE DICTIONARY")
        retVal = False
    return retVal

def executeAction(vmObject, actionData):
    if 'WAIT_SECONDS' in actionData:
        scheduleDelay = actionData['WAIT_SECONDS']
    else:
        scheduleDelay = 30
    vmObject.powerOn()
    vmReady = False
    retVal = True
    while vmReady is False:
        vmReady = vmObject.waitForVmToBoot()
    time.sleep(10)
    if actionData['TYPE'] == "COMMANDS":
        retVal = runCommands(vmObject, actionData)
    if actionData['TYPE'] == "SCRIPT":
        retVal = runScript(vmObject, actionData)
    time.sleep(scheduleDelay)
    if 'SUCCESS_TYPE' in actionData and 'SUCCESS_METRIC' in actionData:
        retVal = checkSuccess(vmObject, actionData)
    vmObject.vmObject.ShutdownGuest()
    time.sleep(10)
    vmObject.powerOff()
    return retVal
    
def parallelRun(serverConfig, vmName, username, password, actionData, snapshotName):
    """
    CREATE SERVER
    """
    logFile = './logs/service_management_' + vmName + '.log'
    try:
        os.remove(logFile)
    except:
        pass

    try:
        logFileObj = open(logFile, 'w')
        logFileObj.write(vmName)
        logFileObj.close()
    except:
        print("FAILED TO OPEN " + logFile)
    vmServer = vm_automation.esxiServer.createFromFile(serverConfig, logFile)
    if vmServer == None:
        print("VM SERVER CREATION FAILED")
        return 0
    
    """
    GET VM OBJECT
    """
    vmObject = sampleLib.getVmObjectFromName(vmServer, vmName)
    vmObject.setUsername(username)
    vmObject.setPassword(password)
    
    if vmObject == None:
        retVal = False
    else:
        retVal = executeAction(vmObject, actionData)
        if retVal != True:
            reVal = False
    if retVal:
        vmObject.takeSnapshot(snapshotName)
    return (vmName, retVal)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", help="action to run")
    parser.add_argument("-k", "--keyword", help="VM search parameter")
    parser.add_argument("-lc", "--listCommands", help="list available commands", action="store_true")
    parser.add_argument("-sn", "--snapshotName", help="name if snapshot to create after changes")
    parser.add_argument("-vf", "--vmFile", help="text file with vms to apply changes")
    parser.add_argument("-w", "--wait", help="override the time (in seconds) to wait after running commands/script")
    parser.add_argument("-cf", "--credsFile", help="credentials file for logging into the vm")
    parser.add_argument("-af", "--actionFile", help="json file containing commands/actions")
    parser.add_argument("-un", "--username", help="vm username")
    parser.add_argument("-pw", "--password", help="vm password")
    parser.add_argument("-t", "--threads", help="concurrent vms to alter")
    parser.add_argument("hypervisorConfig", help="json hypervisor config")
    args = parser.parse_args()

    """
    PREP COMMAND FILE
    """
    if args.actionFile != None:
        commandFile = args.actionFile
    else:
        commandFile = "./action_scripts/commands.json"
    commandDictionary = sampleLib.loadJsonFile(commandFile)
    if commandDictionary == None:
        print("FAILED TO LOAD COMMANDS")
        return 0
    """
    IF THEY ASK TO LIST COMMANDS, DO IT AND EXIT
    """
    if args.listCommands:
        return listCommands(commandDictionary)
    
    """
    ENSURE THE COMMAND EXISTS
    """
    if args.action not in commandDictionary:
        print("SELECTED ACTION NOT LISTED IN COMMAND FILE")
        listCommands(commandDictionary)
        return 0
    
    """
    CHECK THAT WE HAVE REQUIRED CREDS SOMEHOW
    """
    if (args.username == None or args.password == None) and args.credsFile == None:
        print("VM CREDENTIALS REQUIRED FOR THIS OPERATION")
        exit(0)

    credsDictionary = None
    if args.credsFile != None:
        credsDictionary = sampleLib.loadJsonFile(args.credsFile)
        if credsDictionary == None:
            print("FAILED TO LOAD CREDS FILE")
            exit(0)
    
    replaceUsername(commandDictionary[args.action], args.username)
    replacePassword(commandDictionary[args.action], args.password)
    """
    UPDATE WAIT, IF REQUIRED
    """
    if args.wait != None:
        commandDictionary[args.action]['WAIT_SECONDS'] = int(args.wait)
        
    """
    CREATE SERVER
    """
    logFile = './logs/service_management.log'
    try:
        os.remove(logFile)
    except:
        pass
    vmServer = vm_automation.esxiServer.createFromFile(args.hypervisorConfig, logFile)
    if vmServer == None:
        print("VM SERVER CREATION FAILED")
        return 0
    
    """
    GENERATE LIST OF VMS THAT NEED TO CHANGE
    """
    vmsToChange = sampleLib.makeVmList(vmServer, args.keyword, args.vmFile)
    
    """
    ARE WE USING THREADS?
    """
    if args.threads != None:
        """
        EXECUTE IN PARALLEL
        """
        pool = multiprocessing.Pool(int(args.threads))
        print("USING " + str(int(args.threads)) + " THREADS")
        vmNames = []
        for vm in vmsToChange:
            vmNames.append(vm.vmName)
        try:
            results = [pool.apply_async(parallelRun, 
                                        args = (args.hypervisorConfig, \
                                                vmName, \
                                                args.username, \
                                                args.password, \
                                                commandDictionary[args.action], \
                                                args.snapshotName)) \
                                        for vmName in vmNames]
        except Exception as e:
            print("CAUGHT EXCEPTION " + str(e))
        pool.close()
        pool.join()
        actualResults = []
        for i in results:
            try:
                actualResults.append(i.get())
            except Exception as e:
                print("EXCEPTION GENERATED: " + str(e))
                continue
        for j in actualResults:
            print(str(j))
    else:
        """
        RUN THE COMMANDS IN SERIAL
        """
        for vm in vmsToChange:
            if credsDictionary != None and vm.vmName in credsDictionary:
                vm.setUsername(credsDictionary[vm.vmName]['USERNAME'])
                vm.setPassword(credsDictionary[vm.vmName]['PASSWORD'])
            else:
                vm.setUsername(args.username)
                vm.setPassword(args.password)
            if vm.getUsername() == None or vm.getPassword() == None:
                print ("NO CREDS AVAILABLE FOR " + vm.vmName)
            else:
                if executeAction(vm, commandDictionary[args.action]):
                    retVal = True
                    if args.snapshotName != None:
                        vm.takeSnapshot(args.snapshotName)
                else:
                    retVal = False
            print(str((vm.vmName, retVal)))
    
if __name__ == "__main__":
    main()
