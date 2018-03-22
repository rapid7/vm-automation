# Created by Aaron Soto (@_surefire_)
# in collaboration with Brendan Watters (@tychos_moose)
# released under the BSD license
# v0.1 (2017-June-25)

# TODO: Test on ESXi 6.0 and 5.5 (only tested with ESXi 6.5)
# TODO: Confirm that snapshots work
# TODO: Determine whether VMX hardware changes between snapshots are copied over
# TODO: Allow cloining from a previous source snapshot to a new destination machine

import esxiVm
import pexpect
import sys
from pyVmomi import vim

class esxiSsh(esxiVm.esxiServer):
    def copyOvfTool(self):
        # TODO: Detect if this version of ovftool is already present on remote server, then return true

        ovfToolsPath = './ovftool-4.2.0-4586971.tgz'
        ovfToolsURL = 'https://my.vmware.com/group/vmware/details?downloadGroup=OVFTOOL420&productId=491'
        try:
            f = open(ovfToolsPath,"rb");
            f.close()
        except IOError:
            print "FATAL ERROR: VMware 'ovftool' is required for server-to-server cloning.  Download it from VMware at:"
            print "   " + ovfToolsURL
            print "and place it in ovfToolsPath: " + ovfToolsPath
            sys.exit(-1)

        session = pexpect.spawn('scp -o ConnectTimeout=5 ' + ovfToolsPath + ' ' + \
                                 self.username + '@' + self.hostname + ":/tmp/ovftool.tgz")
        i = session.expect(['Are you sure you want to continue connecting (yes/no)?', 'Password:', 'Connection refused', 'Connection timed out'])

        if i == 0:
            # Are you sure you want to continue connecting (yes/no)?
            session.sendline('yes')
            session.expect('Password:')
            session.sendline(self.password)
        if i == 1:
            # Password:
            session.sendline(self.password)
        if i == 2:
            self.fatalError("Connection refused.  Confirm that SSH is enabled on the ESXi server")
            # Connection refused
        if i == 3:
            self.fatalError("Connection refused.  Confirm the IP address and that SSH is permitted on host.")
            # Connection timed out

        session.expect('100%')
        return True

    def cloneToServer(self, srcVm, destServer, destDatastore, destVm, timeout=60*30):
        # Copying between servers takes a while, so the default timeout is 30 minutes.
        if type(srcVm) != str or type(destVm) != str:
            fatalError("Source and destination VMs must be the VM names as strings.")
        elif type(destDatastore) != str:
            fatalError("Destination datastore must be a string.")
        elif type(destServer) != str:
            fatalError("Destination datastore must be the IP address as a string.")

        path, srcVmdk = self.findVmdkPath(srcVm)

        session = self.loginToEsx()

        # Configure source server firewall to allow outbound SSH and HTTP
        self.toggleFirewallRules(session,enabled=True)

        # Deploy OVF Tool on source server
        self.deployOvfTool(session)

        srcServer = self.username + ":" + self.password + "@" + self.hostname
        session.sendline('/tmp/ovftool/ovftool -dm=thin -ds=' + destDatastore \
                         + ' --name=' + destVm + ' vi://' + srcServer + '/' + srcVm \
                         + ' vi://' + destServer)
        # TODO: Fill in the following for success, timeout/refused, and name already exists
        i = session.expect(['Completed successfully','Error: Internal error: Failed to connect to server','Error: Duplicate name','Invalid target datastore specified','No network mapping specified'],timeout=timeout)
        if i == 0:
            # Completed successfully
            return True
        elif i == 1:
            # Error: Internal error: Failed to connect to server
            #   (Note: This occurs when there's a timeout or connection refused.  No way to discern the difference.)
            self.fatalError("Unable to connect to destination server.  Connection timed out or refused.")
        elif i == 2:
            # Error: Duplicate name
            self.fatalError("VM name already exists on destination server")
        elif i == 3:
            # Invalid target datastore specified
            self.fatalError("Datastore name not found on destination server")
        elif i == 4:
            # No network mapping specified.
            self.fatalError("Destination server is missing the case-sensitive network name required by this VM.")
        session.interact()

    def deployOvfTool(self,session):
        # Clear any previous files/directories
        session.sendline('rm -rf /tmp/ovftool*')

        # SCP the OVF tool to the source server
        self.copyOvfTool()

        # Deploy the OVF tool
        session.sendline('mkdir /tmp/ovftool')
        session.sendline('tar xf /tmp/ovftool.tgz -C /tmp/ovftool')

        # Confirm OVF tool deployed properly
        session.sendline('/tmp/ovftool/ovftool --version')
        session.expect('VMware ovftool',timeout=5)

    def toggleFirewallRules(self,session,enabled=False):
        prompt = ':~]'
        session.expect(prompt)

        for service in ['sshClient','httpClient']:
            session.sendline('esxcli network firewall ruleset set -e ' + str(enabled).lower() + \
                             ' -r ' + service)
            session.expect(prompt)

    def clone(self, srcVm, destVm, thinProvision=True):
        # srcVm = string, name of source VM
        # destVm = string, name of destination VM
        #    Limitations:
        #         Source VM must exist on one datastore
        #         Source VM name must be unique
        #         esxiServer must not be a vCenter server
        #         VM cannot contain multiple disks

        if type(srcVm) != str or type(destVm) != str:
            fatalError("Source and destination VMs must be the VM names as strings.")

        path, srcVmdk = self.findVmdkPath(srcVm)

        session = self.loginToEsx()

        # Make destination directory
        session.sendline('cd ' + path)
        session.sendline('mkdir ' + destVm)
        session.sendline('ls ' + path + '/' + destVm)

        # Copy non-VMDK files from source VM to destination VM
        session.sendline('find "' + path + '/' + srcVm + '" -maxdepth 1 -type f | grep -v ".vmdk"' + \
                         ' | while read file; do cp "$file" "' + path + '/' + destVm + '"; done')

        # Copy VMDK files from source VM to destination VM
        destVmdk = srcVmdk.split('/')[-1]
        if thinProvision:
            session.sendline('vmkfstools -i "' + path + '/' + srcVmdk + '" -d thin "' \
                             + path + '/' + destVm + '/' + destVmdk + '"')
        else:
            session.sendline('vmkfstools -i "' + path + '/' + srcVmdk + '" -d zeroedthick "' \
                             + path + '/' + destVm + '/' + destVmdk + '"')

        # Wait for the VMDK copying to complete, and check for errors
        while True:
            i = session.expect(["Clone: 100% done.","Failed to clone disk","Failed to lock the file"], timeout=60*30)
            if i == 0:
                break
            elif i == 1:
                try:
                    session.expect("The file already exists", timeout=1)
                    self.fatalError("The VMDK already exists.  Pick a different destination VM name, or clean up your datastore first.")
                    return False
                except pexpect.TIMEOUT:
                    self.fatalError("An unknown error occured copying the VMDK.  Here, have a shell:")
                    session.interact()
            elif i == 2:
                self.fatalError("Unable to lock the VMDK file.  The VM must be powered off.")
                return False

        # One last thing, register the new VM in the ESXi inventory
        session.sendline('vim-cmd solo/registervm ' + path + '/' + destVm + '/' + srcVm + '.vmx ' \
                         + destVm)
        try:
            i = session.expect(['^[0-9]+$'], timeout=30)
            if i == 0:
                print session.before
                print session.after
            else:
                print "???"
            return True
        except pexpect.TIMEOUT:
            return False

        session.sendline("exit")
        session.expect(["Connection to .* closed."],timeout=10)

    def loginToEsx(self):
        session = pexpect.spawn('ssh -o ConnectTimeout=5 ' + self.username + '@' + self.hostname)
        i = session.expect(['Are you sure you want to continue connecting (yes/no)?', 'Password:', 'Connection refused', 'Connection timed out'])
        if i == 0:
            # Are you sure you want to continue connecting (yes/no)?
            session.sendline('yes')
            session.expect('Password:')
            session.sendline(self.password)
        if i == 1:
            # Password:
            session.sendline(self.password)
        if i == 2:
            self.fatalError("Connection refused.  Confirm that SSH is enabled on the ESXi server")
            # Connection refused
        if i == 3:
            self.fatalError("Connection refused.  Confirm the IP address and that SSH is permitted on hte ESXi firewall")
            # Connection timed out
        return session

    def findVmdkPath(self, srcVm):
        # srcVm could be a name (str), a vmId (int), or a vm object (vmObject)
        # destVm must be a name (what about workstation?  where will I store the new VM?)
        #                        what about ESXi?  What datastore should I use?

        self.enumerateVms()

        if type(srcVm) == str:
            datastore, srcVmdk = self.findVmdkByName(srcVm)

        if not datastore or not srcVmdk:
            self.fatalError("Source VMDK could not be located")

        path = self.findDatastorePath(datastore)

        return path, srcVmdk

    def findVmdkByName(self,srcVm):
        vmObject = None

        for vm in self.vmList:
            if vm.vmName == srcVm and vmObject == None:
                vmObject = vm.vmObject
            elif vm.vmName == srcVm:
                self.fatalError("Unable to identify source VM.  Multiple VMs have that name")

        if vmObject == None:
            self.fatalError("Unable to identify source VM.  No VM found with that name")

        if len(vmObject.config.datastoreUrl) > 1:
            self.fatalError("VM uses multiple datastores")

        src = None

        path = vmObject.config.datastoreUrl[0].url
        for device in vmObject.config.hardware.device:
           if str(type(device)) == "<class 'pyVmomi.VmomiSupport.vim.vm.device.VirtualDisk'>":
               if src == None:
                   src = device.backing.fileName
               else:
                   self.fatalError("VM has multiple disks")

        (datastore,srcVmdk) = src.split(" ")
        datastore = datastore[1:-1]

        return datastore,srcVmdk

    def findDatastorePath(self,datastoreName):
        content = self.connection.content
        objView = content.viewManager.CreateContainerView(content.rootFolder,
                                                          [vim.HostSystem],
                                                          True)
        view = objView.view
        objView.Destroy()

        if len(view) > 1:
            self.fatalError("Multiple ESXi hosts found.  You must connect to the ESXi server directly, not vCenter")

        datastores = view[0].configManager.storageSystem.fileSystemVolumeInfo.mountInfo

        for datastore in datastores:
            if datastore.volume.type == "VMFS" and datastore.volume.name == datastoreName:
                return datastore.mountInfo.path

    def fatalError(self,str):
        print "FATAL ERROR:", str
        sys.exit(-1)


##########
# Example usage:
##########

# REQUIRED: First, connect to the ESXi server with the source image
# myserver = esxiSsh("192.168.1.1", "root", "password", "443", "esxi-192-168-1-1.log")
# myserver.connect()

# Copy a VM locally within myserver
# myserver.clone("sourceVmName","destinationVmName")

# Copy a VM from myserver to 192.168.1.2
# myserver.cloneToServer("sourceVmName","root:password@192.168.1.2","destinationDatastore","destinationVmName")
