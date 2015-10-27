
from pyVmomi import vim
from pyVim import connect
from jnpr.junos.factory.factory_loader import FactoryLoader
from jnpr.junos import Device
from threading import Thread
import atexit, sys, getopt, requests, ssl, argparse, re, yaml

global phy_port


yml = '''
---
EtherSwTable:
  rpc: get-interface-ethernet-switching-table
  item: ethernet-switching-table/mac-table-entry[mac-type='Learn']
  key: mac-address
  view: EtherSwView

EtherSwView:
  fields:
    vlan_name: mac-vlan
    mac: mac-address
    mac_type: mac-type
    interface: mac-interfaces-list/mac-interfaces
'''
globals().update(FactoryLoader().load(yaml.load(yml)))


### Disable Cert request for vCenter 5.5

requests.packages.urllib3.disable_warnings()

# Remove HTTPS verification
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

### End disable Cert request



### Connect to Juniper Device
def ConnectJuniper():
    

    global dev
    print '\n\n' + "Establish connection to Juniper System..." + '\t\t\n',
    dev=Device(host='Insert_Device', user="Insert_user", password="Insert_password")
    dev.open()

### EndConnect to Juniper Device

### Connect to vCenter Device
def ConnectvCenter():

    global content
    print "Establish connection to Juniper VMware vCenter" + '\t\t\n', 
    service_instance = connect.SmartConnect(host='Insert_Device',
                                            user='Insert_user',
                                            pwd='Insert_password',
                                            port=int(443))
    
    atexit.register(connect.Disconnect, service_instance)
    content = service_instance.RetrieveContent()

### End Connect to vCenter Device

### Matching the correct syntax for port on Junos. Eg, ge-0/0/0
def valid_syntax(port):
    
    pattern = re.compile(r'^[ge|xe|et]+-[0-99]+/[0-99]+/[0-99]+\Z')

    if pattern.match(port):
            return port
    

    msg = "Not a valid format: '{0}'.".format(port)
    raise argparse.ArgumentTypeError(msg)
### End Matching the correct syntax for port on Junos


### Retrieving all VM's registered on vCenter
def GetVMs(content):
    print("Getting all VMs" + '\t\t\t\t\t\t'),
    vm_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.VirtualMachine],
                                                      True)
    obj = [vm for vm in vm_view.view]
    vm_view.Destroy()
    print("[Done]")
    return obj

### Collecting all MAC addresses on the Junos device attached to the selected port
def Collect_Mac_Map(phy_port):

    print("Collecting learned MAC from specified interface" + '\t\t'),
    swlist = EtherSwTable(dev)
    swlist.get()
    obj = set()
    for myloop in swlist:
        if (myloop.interface == phy_port):
            obj.add (myloop.mac) 
    print("[Done]")
    return obj


### Matches the Mac addresses seen on the Junos device to the mac adresses found on vCenter
def mac_vm_matching(vms):
    matchlist = {}
    macmatchlist = set()
    macmatchlist = Collect_Mac_Map(phy_port)
    obj = {}
    
    for vm in vms:

        obj = mac_match(vm, macmatchlist, matchlist)

    return obj

def mac_match(vm, macmatchlist, matchlist):
    

    for target in vm.config.hardware.device:
        if isinstance(target, vim.vm.device.VirtualEthernetCard):

            if (target.macAddress) in macmatchlist:
                matchlist[target.macAddress]=vm.name
    
    
    return matchlist
    



### Arguments required



parser = argparse.ArgumentParser(description='This is a PyMOTW sample program')
parser.add_argument('-p', "--port", help="Enter port - format (ge, xe, et) -n/n/n ", required=True, type=valid_syntax)
parser.add_argument('-u', "--unit", help="Enter port - format n ", required=True)

results = parser.parse_args()

phy_port = results.port +'.' + results.unit



### End Arguments required


### Multitheaded connection to vCenter and Juniper
ConnectJ = Thread(target = ConnectJuniper, args=())
ConnectV = Thread(target = ConnectvCenter, args=())
ConnectJ.start()
ConnectV.start()

ConnectJ.join()
ConnectV.join()

### End Multitheaded connection to vCenter and Juniper
 
vms = GetVMs(content)

for key, value in mac_vm_matching(vms).iteritems() :
    print phy_port +'\t\t' + key +'\t\t' + value

