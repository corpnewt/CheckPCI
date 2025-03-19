# CheckPCI
Py script to list PCI devices detected in ioreg.

***

```
usage: CheckPCI.py [-h] [-f FIND_NAME] [-i LOCAL_IOREG]

CheckPCI - a py script to list PCI device info from the IODeviceTree.

options:
  -h, --help            show this help message and exit
  -f, --find-name FIND_NAME
                        find device paths for objects with the passed name
                        from the IODeviceTree
  -i, --local-ioreg LOCAL_IOREG
                        path to local ioreg dump to leverage
```

***

The output columns use short-hand descriptors which aren't obvious.  A quick explainer for those is as follows:

* `PCIDBG` - this shows the bus, device, and function addresses for the PCI device using the format `BB:DD.F`.  These are pulled and converted from the `pcidebug` property.
* `VEN:DEV` - this is the hexadecimal vendor and device ids of the device.
* `Built-In` - a `YES` or `NO` value denoting whether the device has the `built-in` or `IOBuiltin` property.
* `Bridged` - a `YES` or `NO` value denoting whether or not any PCI bridges that lack ACPI device definitions exist in the device's path.  If this is `YES`, you may need to define those devices in ACPI in order for `DeviceProperties` to inject early enough to take effect.
* `ACPI+DevicePaths` - the ACPI or device paths corresponding to the PCI device.  The ACPI paths lack the `_SB` or `_PR` entry, and may not be accurate due to the potential for renamed devices.
