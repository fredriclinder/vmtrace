This is a python tool to map vCenter Virtual Machines attached to logical interfaces on a Juniper Junos device. 
It utilizes the VMware pyVmomi SDK and the PyEZ repositories from Juniper Networks
 
NOTE: It does not work with VMware NSX, but will will map standard vSwitches and distributed vSwitches.
 
 
It will extract VM information from vCenter
Map it to the specified interface using the PyEZ tables: EthPortTable  and VlanTable 
