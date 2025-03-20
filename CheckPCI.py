import os, sys, binascii, argparse
from Scripts import ioreg, utils

class CheckPCI:
    def __init__(self):
        # Verify running OS
        if not sys.platform.lower() == "darwin":
            print("This script can only be run on macOS!")
            exit(1)
        self.u = utils.Utils("CheckPCI")
        self.i = ioreg.IOReg()
        self.default_columns = (
            ("PCIDBG",7),
            ("VEN:DEV",9),
            ("Built-In",8),
            ("Bridged",7),
            ("ACPI",0),
            ("Device",0)
        )

    def main(self,device_name=None,columns=None):
        if device_name is not None and not isinstance(device_name,str):
            device_name = str(device_name)
        display_columns = []
        if isinstance(columns,(list,tuple)):
            for c in columns:
                try:
                    c = int(c)-1
                    self.default_columns[c]
                    if not c in display_columns:
                        display_columns.append(c)
                except:
                    pass
        else:
            display_columns = list(range(len(self.default_columns)))
        if not display_columns:
            print("No columns to display!")
            exit(1)
        all_devs = self.i.get_all_devices()
        dev_list = []
        for p in all_devs.values():
            p_dict = p.get("info",{})
            ven = p_dict.get("vendor-id")
            dev = p_dict.get("device-id")
            if not (ven and dev):
                continue # Missing info - skip
            # Check our name if we are looking for one
            if device_name and not p.get("name_no_addr","").lower() == device_name.lower():
                continue # Not our device name - skip
            # Set defaults
            pcidebug = vendev = builtin = bridged = acpi = device = ""
            # Check if we're getting the pcidebug info
            if 0 in display_columns:
                pcidebug = "??:??.?"
                if "pcidebug" in p_dict:
                    # Try to organize it the same way gfxutil does
                    try:
                        a,b,c = p_dict["pcidebug"].strip('"').split("(")[0].split(":")
                        pcidebug = "{}:{}.{}".format(
                            hex(int(a))[2:].rjust(2,"0"),
                            hex(int(b))[2:].rjust(2,"0"),
                            hex(int(c))[2:]
                        )
                    except Exception as e:
                        print(e)
                        pass
                pcidebug = pcidebug.ljust(self.default_columns[0][1])
            # Check if we're getting the ven:dev info
            if 1 in display_columns:
                vendev = "????:????"
                try:
                    ven = binascii.hexlify(binascii.unhexlify(ven[1:5])[::-1]).decode()
                    dev = binascii.hexlify(binascii.unhexlify(dev[1:5])[::-1]).decode()
                    vendev = "{}:{}".format(ven,dev)
                except:
                    pass
                vendev = vendev.ljust(self.default_columns[1][1])
            # Check if we're getting the built-in info
            if 2 in display_columns:
                builtin = "NO"
                if "built-in" in p_dict or "IOBuiltin" in p_dict:
                    builtin = "YES"
                builtin = builtin.ljust(self.default_columns[2][1])
            # Check if we're getting the bridged info
            if 3 in display_columns:
                bridged = "YES"
                if p_dict.get("acpi-path"):
                    bridged = "NO"
                bridged = bridged.ljust(self.default_columns[3][1])
            # Check if we're getting the ACPI path
            if 4 in display_columns:
                acpi = p.get("acpi_path","Unknown APCI Path")
            # Check if we're getting the device path
            if 5 in display_columns:
                device = p.get("device_path","Unknown Device Path")
            # Join the info together
            acpi_device = " = ".join([x for x in (acpi,device) if x])
            final_column = " ".join([x for x in (pcidebug,vendev,builtin,bridged,acpi_device) if x])
            # Add to the list
            dev_list.append(final_column)
        if not dev_list:
            # Nothing was returned - adjust output based on
            # whether or not we're searching
            if device_name is None:
                print("No PCI devices located!")
            else:
                print("No device matching '{}' was found!".format(device_name))
            exit(1)
        # Gather our column headers
        header_list = []
        for i in sorted(display_columns):
            _head,_adj = self.default_columns[i]
            header_list.append(_head.ljust(_adj))
        # Join "ACPI" and "Device" with a "+"
        if header_list[-2:] == ["ACPI","Device"]:
            header_list = header_list[:-2]+["ACPI+Device"]
        dev_header = " ".join(header_list)
        if dev_header.endswith(("ACPI","Device")):
            dev_header += " Paths"
        dev_list = [dev_header,"-"*len(dev_header)]+sorted(dev_list)
        print("\n".join(dev_list))

if __name__ == '__main__':
    # Create our object to get values for the help output
    p = CheckPCI()
    available = ", ".join("{} - {}".format(i,x[0]) for i,x in enumerate(p.default_columns,start=1))
    # Setup the cli args
    parser = argparse.ArgumentParser(prog="CheckPCI.py", description="CheckPCI - a py script to list PCI device info from the IODeviceTree.")
    parser.add_argument("-f", "--find-name", help="find device paths for objects with the passed name from the IODeviceTree")
    parser.add_argument("-i", "--local-ioreg", help="path to local ioreg dump to leverage")
    parser.add_argument("-c", "--column-list", help="comma delimited list of numbers representing which columns to display.  Options are:\n{}".format(available))
    args = parser.parse_args()
    if args.local_ioreg:
        ioreg_path = p.u.check_path(args.local_ioreg)
        if not ioreg_path:
            print("'{}' does not exist!".format(args.local_ioreg))
            exit(1)
        elif not os.path.isfile(ioreg_path):
            print("'{}' is not a file!".format(args.local_ioreg))
            exit(1)
        # Try loading it
        try:
            with open(ioreg_path,"rb") as f:
                p.i.ioreg["IOService"] = f.read().decode(errors="ignore").split("\n")
        except Exception as e:
            print("Failed to read '{}': {}".format(args.local_ioreg,e))
            exit(1)
        print("Using local ioreg: {}".format(ioreg_path))
    columns = None
    if args.column_list:
        # Ensure we have values that are valid
        columns = []
        _max = len(p.default_columns)
        for x in args.column_list.split(","):
            try:
                if "-" in x:
                    a,b = map(int,x.strip().split("-"))
                    assert 0 < a <= _max
                    assert 0 < b <= _max
                    a,b = min(a,b),max(a,b)
                    for c in range(a,b+1):
                        if not c in columns:
                            columns.append(c)
                else:
                    c = int(x.strip())
                    assert 0 < c <= _max
                    if not c in columns:
                        columns.append(c)
            except:
                pass
        if not columns:
            print("Invalid column information passed.  Can only accept comma delmited numbers from")
            print("1-{} corresponding to the following:".format(_max))
            print(available)
            exit(1)
    p.main(device_name=args.find_name,columns=columns)
