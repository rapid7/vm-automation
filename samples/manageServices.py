import argparse
import signal
import vm_automation
import multiprocessing
import os
import time
from tqdm import tqdm
from pyVmomi import vim
import sampleLib


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
    return retVal

def runExe(vmObject, actionData):
    localFileName = actionData['FILENAME']
    remoteFileName = actionData['UPLOAD_DIR'] + "\\" + localFileName.split('/')[-1]
    retVal = False
    try:
        retVal = vmObject.uploadAndRun(localFileName, remoteFileName, "", True)
    except Exception as e:
        print("CAUGHT EXCEPTION: " + str(e))
    return retVal


def checkSuccess(vmObject, actionData):
    retVal = False
    if 'SUCCESS_TYPE' in actionData and 'SUCCESS_METRIC' in actionData:
        if actionData['SUCCESS_TYPE'] == 'PROCESS':
            retVal = sampleLib.checkForProcess(vmObject, actionData['SUCCESS_METRIC'])
    else:
        print("NO SUCCESS_TYPE OR SUCCESS METRIC IN THE DICTIONARY")
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
    try:
        if actionData['TYPE'] == "COMMANDS":
            retVal = runCommands(vmObject, actionData)
        if actionData['TYPE'] == "EXE":
            retVal = runExe(vmObject, actionData)
        if actionData['TYPE'] == "SCRIPT":
            retVal = runScript(vmObject, actionData)
        time.sleep(scheduleDelay)
        if 'SUCCESS_TYPE' in actionData and 'SUCCESS_METRIC' in actionData:
            retVal = checkSuccess(vmObject, actionData)
    except Exception as e:
        print ("Exception processing " + vmObject.vmName)
        print (str(e))
    vmObject.vmObject.ShutdownGuest()
    time.sleep(10)
    vmObject.powerOff()
    return retVal


def parallelRun(serverConfig, vmName, username, password, actionData, snapshotName):
    """
    CREATE SERVER
    """
    logPath = './logs'
    if not os.path.exists(logPath):
        os.makedirs(logPath)

    logFile = os.path.join(logPath, "service_management_" + vmName + ".log")
    try:
        logFileObj = open(logFile, 'w')
        logFileObj.write(vmName)
        logFileObj.close()
    except:
        print("FAILED TO OPEN " + logFile)
    vmServer = vm_automation.esxiServer.createFromFile(serverConfig, logFile)
    if vmServer is None:
        print("VM SERVER CREATION FAILED")
        return 0
    
    """
    GET VM OBJECT
    """
    vmObject = vmServer.getVmByName(vmName)
    vmObject.setUsername(username)
    vmObject.setPassword(password)
    
    if vmObject is None:
        retVal = False
    else:
        retVal = executeAction(vmObject, actionData)
    if retVal and snapshotName is not None:
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
    if args.actionFile is not None:
        commandFile = args.actionFile
    else:
        commandFile = "./action_scripts/commands.json"
    commandDictionary = sampleLib.loadJsonFile(commandFile)
    if commandDictionary is None:
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
    if args.credsFile is not None:
        credsDictionary = sampleLib.loadJsonFile(args.credsFile)
        if credsDictionary is None:
            print("FAILED TO LOAD CREDS FILE")
            exit(0)

    replaceUsername(commandDictionary[args.action], args.username)
    replacePassword(commandDictionary[args.action], args.password)
    """
    UPDATE WAIT, IF REQUIRED
    """
    if args.wait is not None:
        commandDictionary[args.action]['WAIT_SECONDS'] = int(args.wait)

    """
    CREATE SERVER
    """
    logPath = './logs'
    if not os.path.exists(logPath):
        os.makedirs(logPath)

    logFile = os.path.join(logPath, "service_management.log")
    vmServer = vm_automation.esxiServer.createFromFile(args.hypervisorConfig, logFile)
    if vmServer is None:
        print("VM SERVER CREATION FAILED")
        return 0
    
    """
    GENERATE LIST OF VMS THAT NEED TO CHANGE
    """
    vmsToChange = sampleLib.makeVmList(vmServer, args.keyword, args.vmFile)

    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

    num_threads = 1
    if args.threads is not None:
        num_threads = args.threads

    pool = multiprocessing.Pool(int(num_threads))
    print("USING " + str(int(num_threads)) + " THREADS")
    try:
        signal.signal(signal.SIGINT, original_sigint_handler)
        results = []

        for vm in vmsToChange:
            vm_user = args.username
            vm_pass = args.password
            if credsDictionary is not None:
                for machine in credsDictionary:
                    if credsDictionary[machine]['NAME'] == vm.vmName:
                        vm_user = credsDictionary[machine]['USERNAME']
                        vm_pass = credsDictionary[machine]['PASSWORD']

            thread_args = [
                args.hypervisorConfig,
                vm.vmName,
                vm_user,
                vm_pass,
                commandDictionary[args.action],
                args.snapshotName
            ]
            results.append(pool.apply_async(parallelRun, args=thread_args))

        with tqdm(total=len(vmsToChange)) as progress:
            current_len = 0
            while current_len < len(vmsToChange):
                num_ready = 0
                for result in results:
                    if result.ready():
                        num_ready += 1
                if num_ready > current_len:
                    progress.update(num_ready - current_len)
                    current_len = num_ready
                else:
                    progress.refresh()
                time.sleep(5)
            progress.update(current_len)
    except KeyboardInterrupt:
        print("User cancel received, terminating processing")
        if pool is not None:
            pool.terminate()
        exit(-1)
    else:
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

if __name__ == "__main__":
    main()
