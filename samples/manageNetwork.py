import argparse
import json
import os
from tqdm import tqdm
from pyVmomi import vim
import vm_automation


def get_vm_server(config_file):
    if os.path.isfile(config_file):
        with open(config_file) as config_file_handle:
            config_map = json.load(config_file_handle)
            if config_map['HYPERVISOR_TYPE'].lower() == "esxi":
                vmServer = vm_automation.esxiServer.createFromConfig(config_map, 'esxi_automation.log')
                vmServer.connect()
            if config_map['HYPERVISOR_TYPE'].lower() == "workstation":
                vmServer = vm_automation.workstationServer(config_map, 'workstation_automation.log')
        return vmServer
    return None


def set_network(vm_server, vm, target_network):
    nic = None
    backing_network = None

    # find the backing network requested
    for network in vm_server.getObject(vim.Network):
        if target_network == network.name:
            backing_network = network
            break

    for device in vm.vmObject.config.hardware.device:
        if isinstance(device, vim.vm.device.VirtualEthernetCard):
            nic = vim.vm.device.VirtualDeviceSpec()
            nic.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
            nic.device = device
            nic.device.wakeOnLanEnabled = True

            nic.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
            nic.device.backing.network = backing_network
            nic.device.backing.deviceName = target_network
            nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            nic.device.connectable.startConnected = True
            nic.device.connectable.allowGuestControl = True

    if nic is not None:
        config = vim.vm.ConfigSpec(deviceChange=[nic])
        task = vm.vmObject.ReconfigVM_Task(config)
        vm.waitForTask(task)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--keyword", help="VM search parameter")
    parser.add_argument("-n", "--network", help="Target network name")
    parser.add_argument("hypervisorConfig", help="json hypervisor config")
    
    args = parser.parse_args()

    network_count = 0
    prefix = args.keyword
    target_network = args.network
    vm_server = get_vm_server(config_file=args.hypervisorConfig)
    if vm_server is None:
        print ("Failed to connect to VM environment")
        exit(1)

    vm_server.enumerateVms()
    for vm in tqdm(vm_server.vmList):
        if prefix in vm.vmName:
            set_network(vm_server, vm, target_network)
            network_count += 1

    print("Task Complete " + str(network_count) + " configurations set")

if __name__ == "__main__":
    main()
