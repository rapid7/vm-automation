import argparse
import vm_automation
import sampleLib

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--keyword", help="VM search parameter")
    parser.add_argument("hypervisorConfig", help="json hypervisor config")
    args = parser.parse_args()
    
    """
    CREATE SERVER
    """
    logFile = './service_management.log'
    vmServer = vm_automation.esxiServer.createFromFile(args.hypervisorConfig, logFile)
    if vmServer == None:
        print("VM SERVER CREATION FAILED")
        return 0
    
    vmList = sampleLib.makeVmList(vmServer, args.keyword, None)
    for vm in vmList:
        print(vm.vmName)

if __name__ == "__main__":
    main()