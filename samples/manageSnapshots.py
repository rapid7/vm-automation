import argparse
import vm_automation

def takeSnapshot(vm, snapshotName, args):
    wasPoweredOn = vm.isPoweredOn()
    if args.powerOn:
        vm.powerOn()
    if args.powerOff:
        vm.powerOff
    retVal = vm.takeSnapshot(args.snapshotName)
    if wasPoweredOn:
        vm.powerOn()
    else:
        vm.powerOff()
    return retVal

def deleteSnapshots(vm, snapshotName):
    vm.getSnapshots()
    for snapshot in vm.snapshotList:
        if snapshot[0].name == snapshotName:
            vm.deleteSnapshot(snapshotName)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--keyword", help="VM search parameter")
    parser.add_argument("-sn", "--snapshotName", help="snapshot name")
    parser.add_argument("-a", "--action", help="action [create|revert|delete]")
    parser.add_argument("-p1", "--powerOn", help="power on vm before snapshot", action="store_true")
    parser.add_argument("-p0", "--powerOff", help="power off vm before snapshot", action="store_true")
    parser.add_argument("hypervisorConfig", help="json hypervisor config")
    
    validActions = ['create', 'revert', 'delete']

    args = parser.parse_args()
    if args.action.lower() not in validActions:
        print('INVALID ACTION')
    if args.keyword != None:
        searchTerm = args.keyword
    if args.snapshotName != None:
        snapshotName = args.snapshotName

    hypervisorDic = {}
    vmServer = vm_automation.esxiServer.createFromFile(args.hypervisorConfig, './snapshot.log')
    if vmServer != None:
        vmServer.enumerateVms()
        for vm in vmServer.vmList:
            if (args.keyword == None) or (searchTerm in vm.vmName):
                if args.action.lower() == 'create':
                    takeSnapshot(vm, args.snapshotName, args)
                if args.action.lower() == 'delete':
                    deleteSnapshots(vm, snapshotName)
                if args.action.lower() == 'revert':
                    vm.revertToSnapshotByName(snapshotName)
    
if __name__ == "__main__":
    main()
