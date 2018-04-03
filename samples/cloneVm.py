import argparse
import vm_automation

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", help="source VM name")
    parser.add_argument("-d", "--destination", help="destination VM name")
    parser.add_argument("hypervisorConfig", help="json hypervisor config")
    args = parser.parse_args()
    
    """
    CREATE SERVER
    """
    logFile = './clone.log'
    vmServer = vm_automation.esxiServer.createFromFile(args.hypervisorConfig, logFile)
    if vmServer == None:
        print("VM SERVER CREATION FAILED")
        return 0
    
    if vmServer.clone(args.source, args.destination, True) is True:
        print("Sucessfully cloned " + args.source + " to " + args.destination)
    else: 
        print("Failed to clone see " + logFile)

if __name__ == "__main__":
    main()
