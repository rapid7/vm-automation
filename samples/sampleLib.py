import json

def checkForProcess(vmObject, processName):
    vmObject.updateProcList()
    if processName in ' '.join(vmObject.procList):
        return True
    else:
        return False

def loadJsonFile(fileName):
    try:
        fileObject = open(fileName, 'r')
        fileStr = fileObject.read()
        fileObject.close()
    except IOError as e:
        print("UNABLE TO OPEN FILE: " + str(fileName) + '\n' + str(e))
        return None
    try:
        fileDic = json.loads(fileStr)
    except Exception as e:
        print("UNABLE TO PARSE FILE: " + str(fileName) + '\n' + str(e))
        return None
    return fileDic

def makeVmList(vmServer, keywordArg, fileArg):
    vmList = []
    if fileArg != None:
        vmFileObj = open(fileArg, 'r')
        desiredVms = vmFileObj.read().splitlines()
        vmFileObj.close()
        vmServer.enumerateVms()
        for vm  in vmServer.vmList:
            if vm.vmName in desiredVms:
                vmList.append(vm)
    if keywordArg != None:
        vmServer.enumerateVms()
        for vm in vmServer.vmList:
            if keywordArg in vm.vmName:
                vmList.append(vm)
    return vmList

def waitForProcess(vmObject, procName, timeout = 600):
    retVal = False
    waitCount = 1
    if timeout > 0:
        waitCount = timeout/5
    for i in range(waitCount):
        vmObject.updateProcList()
        if procName in ' '.join(vmObject.procList):
            retVal = True
            break
        time.sleep(5)
    return retVal
