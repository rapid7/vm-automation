import argparse
import vm_automation


def deleteSnapshots(vm, snapshotSubstring):
    vm.getSnapshots()
    for snapshot in vm.snapshotList:
        if snapshotSubstring in snapshot[0].name:
            vm.deleteSnapshot(snapshot[0].name)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--keyword", help="VM search parameter")
    parser.add_argument("-ss", "--snapshotSubstring", help="snapshot substring")
    parser.add_argument("hypervisorConfig", help="json hypervisor config")
    
    args = parser.parse_args()
    if args.keyword != None:
        searchTerm = args.keyword
    if args.snapshotSubstring != None:
        snapshotSubstring = args.snapshotSubstring

    hypervisorDic = {}
    vmServer = vm_automation.esxiServer.createFromFile(args.hypervisorConfig, './snapshot.log')
    if vmServer != None:
        vmServer.enumerateVms()
        for vm in vmServer.vmList:
            if (args.keyword == None) or (searchTerm in vm.vmName):
                deleteSnapshots(vm, snapshotSubstring)
    
if __name__ == "__main__":
    main()
