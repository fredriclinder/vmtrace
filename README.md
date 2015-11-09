# vmtrace
#
#This is a python tool to map vCenter Virtual Machines to logical interface on a Juniper Junos device. 
#It utilizes the VMware pyVmomi SDK and the PyEZ repositories from Juniper Networks
#
#NOTE: It does not work with VMware NSX, but will will map standard vSwitches and distributed vSwitches.
#
#
#It will extract VM information from vCenter
#Map it to the specified interface using the PyEZ tables: EthPortTable  and VlanTable 
#
#Output example:
#
#ubuntu:systest$ python vmtracep.py --port ge-2/0/35 --unit 0
#Established connection to Juniper VMware vCenter
#Established connection to Juniper System...
#
#
#Interface	VLAN ID		VM MAC			Virtual Machine Name
#ge-2/0/35.0	105		00:50:56:a8:1a:e9	windows7.mydomain.local
#ge-2/0/35.0	201		00:50:56:a8:85:41	w2k10-1.mydomain.local
#ge-2/0/35.0	201		00:50:56:a8:d4:29	w2k10-2.mydomain.local
#ge-2/0/35.0	201		00:50:56:a8:52:54	w2k10-3.mydomain.local
#ge-2/0/35.0	107		00:50:56:a8:b1:f2	w2k10-3.mydomain.local
#ge-2/0/35.0	107		00:50:56:a8:0c:bb	MAAS.mydomain.local
#ge-2/0/35.0	105		00:50:56:a8:24:d6	JunosSpace.mydomain.local
#ge-2/0/35.0	107		00:50:56:a8:c8:91	OpenContrail1.mydomain.local
#ge-2/0/35.0	105		00:50:56:a8:a6:13	OpenContrail2.mydomain.local
#ge-2/0/35.0	201		00:50:56:11:11:11	OpenContrail3.mydomain.local
#ge-2/0/35.0	201		00:50:56:a8:f6:3c	MySQL-1.mydomain.local
#
#ubuntu:systest$
