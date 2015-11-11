

from pyVmomi import vim
from pyVim import connect
from jnpr.junos.factory.factory_loader import FactoryLoader
from jnpr.junos import Device
from threading import Thread
import atexit
import requests
import ssl
import argparse
import re
import requests
import yaml

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

# Disable Cert request for vCenter 5.5
requests.packages.urllib3.disable_warnings()
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Connect to Juniper Device
def ConnectJuniper(jhost, juser, jpassword):


    global dev
    dev=Device(host=jhost, user=juser, password=jpassword)
    dev.open()
    print "Established connection to Juniper System..."

# Connect to vCenter Device
def ConnectvCenter(vhost, vuser, vpassword):

    global content

    service_instance = connect.SmartConnect(host=vhost,
                                            user=vuser,
                                            pwd=vpassword,
                                            port=int(443))

    atexit.register(connect.Disconnect, service_instance)
    content = service_instance.RetrieveContent()
    print "Established connection to Juniper VMware vCenter"

# Matching the correct syntax for port on Junos. Eg, ge-0/0/0
def valid_syntax(port):

    pattern = re.compile(r'^[ge|xe|et]+-[0-99]+/[0-99]+/[0-99]+\Z')

    if pattern.match(port):
            return port


    msg = "Not a valid format: '{0}'.".format(port)
    raise argparse.ArgumentTypeError(msg)

# Retrieving all VM's registered on vCenter
def GetVMs(content):

    vm_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.VirtualMachine],
                                                      True)
    obj = [vm for vm in vm_view.view]
    vm_view.Destroy()
    return obj

# Collecting all MAC addresses on the Junos device attached to the selected port
def Collect_Mac_Map(phy_port):


    swlist = EtherSwTable(dev)
    swlist.get()
    obj = {}
    for myloop in swlist:
        if (myloop.interface == phy_port):
            obj[myloop.mac] = myloop.vlan_name


    return obj

# Collecting all VLAN's
def Collect_VLAN_Map():


    vlanlist = VLTable(dev)
    vlanlist.get()
    obj = {}


    for myloop in vlanlist:

        obj[myloop.vlanname] = myloop.vlantag

    return obj

# Matches the Mac addresses seen on the Junos device to the mac adresses found on vCenter
def mac_vm_matching(vms, phy_port):

    matchlist = {}
    macmatchlist = Collect_Mac_Map(phy_port)


    obj = {}

    for vm in vms:

        obj = mac_match(vm, macmatchlist, matchlist)


    return obj
def mac_match(vm, macmatchlist, matchlist):


    for target in vm.config.hardware.device:
        if (target.key >= 4000) and (target.key < 5000):
            if (target.macAddress) in macmatchlist:
                matchlist[target.macAddress]=(vm.name, macmatchlist[target.macAddress],vm.summary.runtime.host.name)

    return matchlist

# Arguments required
parser = argparse.ArgumentParser(description='vmtrace')
parser.add_argument('-p', "--port", help="Enter port - format (ge, xe, et) -n/n/n ", required=True, type=valid_syntax)
parser.add_argument('-u', "--unit", help="Enter unit - format n ", required=True)
parser.add_argument('-s', "--sort", help="Enter sort option -  mac, vlan, vmname ", required=False, choices=['mac', 'vlan', 'vmname'])
results = parser.parse_args()
if results.sort == ('mac'): sort_type = 0
elif results.sort == 'vlan': sort_type = 1
elif results.sort == 'vmname': sort_type = 2

# Connection requirements
juniper_device = 'juniper_device'
juser = 'user'
jpassword = 'password'

virtualcenter_device = 'virtualcenter_device'
vuser = 'user'
vpassword = 'password'

# Multitheaded connection to vCenter and Juniper
ConnectJ = Thread(target = ConnectJuniper, args=(juniper_device, juser, jpassword))
ConnectV = Thread(target = ConnectvCenter, args=(virtualcenter_device, vuser, vpassword))
ConnectJ.start()
ConnectV.start()
ConnectJ.join()
ConnectV.join()

# main start
phy_port = results.port +'.' + results.unit
matchlist = []
vlans = Collect_VLAN_Map()
vms = GetVMs(content)

# Create the matchinglist
for key, value in mac_vm_matching(vms, results.port +'.' + results.unit).iteritems() :
    vmname, vlan_desc, esxihost = value
    vlan_desc = vlans[vlan_desc]
    matchlist.append([key, vlan_desc, vmname, esxihost])

# Sort the matchinglist pased on args value
sortedlist = sorted(matchlist, key=lambda tup: tup[sort_type])

print '\n\n' + 'Interface' +'\t' + 'VLAN ID' + '\t\t' + 'VM MAC' + '\t\t\t' + 'VMware Host' + '\t\t' + 'Virtual Machine Name'
for value in sortedlist:
    key, vlan_desc, vmname, esxihost  = value
    print results.port +'.' + results.unit +'\t' +vlan_desc + '\t\t'  + key +'\t' + esxihost +'\t\t' + vmname

# Close connections
dev.close()