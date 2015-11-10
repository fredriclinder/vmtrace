

from pyVmomi import vim
from pyVim import connect
from jnpr.junos.factory.factory_loader import FactoryLoader
from jnpr.junos import Device
from jnpr.junos.op.vlan import VlanTable
from threading import Thread
import atexit, sys, getopt, requests, ssl, argparse, re, yaml, pprint

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

VLTable:
  rpc: get-vlan-information
  item: vlan
  key: vlan-tag
  view: VLView

VLView:
  fields:
    vlanname: vlan-name
    vlantag: vlan-tag
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
def ConnectJuniper(host, user, password):


    global dev
    dev=Device(host='Juniper Device', user='user', password='password')
    dev.open()
    print "Established connection to Juniper System..."

### EndConnect to Juniper Device

### Connect to vCenter Device
def ConnectvCenter(host, user, password):

    global content

    service_instance = connect.SmartConnect(host=host,
                                            user=user,
                                            pwd=password,
                                            port=int(443))


    atexit.register(connect.Disconnect, service_instance)
    content = service_instance.RetrieveContent()
    print "Established connection to Juniper VMware vCenter"

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

    vm_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.VirtualMachine],
                                                      True)
    obj = [vm for vm in vm_view.view]
    vm_view.Destroy()
    return obj

### Collecting all MAC addresses on the Junos device attached to the selected port
def Collect_Mac_Map(phy_port):


    swlist = EtherSwTable(dev)
    swlist.get()
    obj = {}
    for myloop in swlist:
        if (myloop.interface == phy_port):
            obj[myloop.mac] = myloop.vlan_name


    return obj


def Collect_VLAN_Map():


    vlanlist = VLTable(dev)
    vlanlist.get()
    obj = {}


    for myloop in vlanlist:

        obj[myloop.vlanname] = myloop.vlantag

    return obj


### Matches the Mac addresses seen on the Junos device to the mac adresses found on vCenter
def mac_vm_matching(vms):
    matchlist = {}
    macmatchlist = Collect_Mac_Map(phy_port)


    obj = {}

    for vm in vms:

        obj = mac_match(vm, macmatchlist, matchlist)


    return obj

def mac_match(vm, macmatchlist, matchlist):


    for target in vm.config.hardware.device:
        if isinstance(target, vim.vm.device.VirtualEthernetCard):

            if (target.macAddress) in macmatchlist:

                matchlist[target.macAddress]=(vm.name, macmatchlist[target.macAddress])

    return matchlist




### Arguments required



parser = argparse.ArgumentParser(description='vmtrace')
parser.add_argument('-p', "--port", help="Enter port - format (ge, xe, et) -n/n/n ", required=True, type=valid_syntax)
parser.add_argument('-u', "--unit", help="Enter unit - format n ", required=True)
parser.add_argument('-s', "--sort", help="Enter sort option -  mac, vlan, vmname ", required=False, choices=['mac', 'vlan', 'vmname'])


results = parser.parse_args()

phy_port = results.port +'.' + results.unit
if results.sort == ('mac'): sort_type = 0
elif results.sort == 'vlan': sort_type = 1
elif results.sort == 'vmname': sort_type = 2

### End Arguments required


### Multitheaded connection to vCenter and Juniper
ConnectJ = Thread(target = ConnectJuniper, args=('juniper_device', 'user', 'password'))
ConnectV = Thread(target = ConnectvCenter, args=('vcenter', 'user', 'password'))

ConnectJ.start()
ConnectV.start()

ConnectJ.join()
ConnectV.join()

### End Multitheaded connection to vCenter and Juniper


### main start

matchlist = []
vlans = Collect_VLAN_Map()
vms = GetVMs(content)

### Create the matchinglist

for key, value in mac_vm_matching(vms).iteritems() :
    vmname, vlan_desc,  = value
    vlan_desc = vlans[vlan_desc]
    matchlist.append([key, vlan_desc, vmname])

### End Create the matchinglist


### Sort the matchinglist pased on args value

sortedlist = sorted(matchlist, key=lambda tup: tup[sort_type])

print '\n\n' + 'Interface' +'\t' + 'VLAN ID' + '\t\t' + 'VM MAC' + '\t\t\t' + 'Virtual Machine Name'
for value in sortedlist:
    key, vlan_desc, vmname  = value
    print phy_port +'\t' +vlan_desc + '\t\t'  + key +'\t' + vmname


dev.close()