# CheckPCI
Py script to list PCI devices detected in ioreg.

***
### Installation
#### Macos and Linux
```
git clone https://github.com/corpnewt/CheckPCI
cd ./CheckPCI
chmod +x ./CheckPCI.command
```

```
usage: CheckPCI.py [-h] [-f FIND_NAME] [-n] [-i LOCAL_IOREG] [-c COLUMN_LIST] [-m [COLUMN_MATCH ...]] [-o OUTPUT_FILE]
                   [-p SAVE_PLIST] [-u]

CheckPCI - a py script to list PCI device info from the IODeviceTree.

options:
  -h, --help            show this help message and exit
  -f, --find-name FIND_NAME
                        find device paths for objects with the passed name from the IODeviceTree
  -n, --include-names   include friendly names for devices where applicable
  -i, --local-ioreg LOCAL_IOREG
                        path relative to this script for local ioreg/powershell to leverage
  -c, --column-list COLUMN_LIST
                        comma delimited list of numbers representing which columns to display. Options are: 1 -
                        PCIDBG, 2 - VEN:DEV, 3 - Built-In, 4 - ACPI, 5 - Device
  -m, --column-match [COLUMN_MATCH ...]
                        match entry formatted as NUM=VAL. e.g. To match all devices that aren't built-in: -m 3=NO
  -o, --output-file OUTPUT_FILE
                        dump the current machine's ioreg/powershell info to the provided path relative to this script
                        and exit
  -p, --save-plist SAVE_PLIST
                        dump all detected PCI devices to the provided path relative to this script and exit
  -u, --update-pci-ids  download the latest pci.ids.gz file from https://pci-ids.ucw.cz and exit
```

***

## The output columns use short-hand descriptors which aren't obvious.  A quick explainer for those is as follows:

* `PCIDBG` - this shows the hexadecimal bus, device, and function addresses for the PCI device using the format `BB:DD.F`.  These are pulled and converted from the `pcidebug` property.
* `VEN:DEV` - this is the hexadecimal vendor and device ids of the device.
* `Built-In` - a `YES` or `NO` value denoting whether all elements of the device path are defined in ACPI or not.  In order for `DeviceProperties` defined in the config.plist to inject early enough to take effect, this must be `YES` - which may require defining missing PCI bridges in ACPI.
* `ACPI+DevicePaths` - the ACPI or device paths corresponding to the PCI device.  The ACPI paths lack the `_SB` or `_PR` entry, and may not be accurate due to the potential for renamed devices.

***

## To get a local ioreg file for troubleshooting, run one of the following depending on your OS:

### Windows from Powershell:
```
Get-PnpDevice -PresentOnly|Where-Object InstanceId -Match '^(PCI\\.*|ACPI\\PNP0A0(3|8)\\[^\\]*)'|Get-PnpDeviceProperty -KeyName DEVPKEY_Device_Parent,DEVPKEY_NAME,DEVPKEY_Device_LocationPaths,DEVPKEY_Device_Address,DEVPKEY_Device_LocationInfo|Select -Property InstanceId,Data|Format-Table -Autosize|Out-String -width 9999 > ioreg.txt
```
### Windows from cmd:
```
powershell -c "Get-PnpDevice -PresentOnly|Where-Object InstanceId -Match '^(PCI\\.*|ACPI\\PNP0A0(3|8)\\[^\\]*)'|Get-PnpDeviceProperty -KeyName DEVPKEY_Device_Parent,DEVPKEY_NAME,DEVPKEY_Device_LocationPaths,DEVPKEY_Device_Address,DEVPKEY_Device_LocationInfo|Select -Property InstanceId,Data|Format-Table -Autosize|Out-String -width 9999" > ioreg.txt
```
### macOS from Terminal:
```
ioreg -lw0 > ioreg.txt
```
The resulting `ioreg.txt` file will be located in the current directory.
***
Alternatively, you can use the `-o [output_file]` CheckPCI switch.

e.g. `CheckPCI.bat/.command -o ./ioreg.txt`
