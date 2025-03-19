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

    def main(self, device_name=None):
        if device_name is not None and not isinstance(device_name,str):
            device_name = str(device_name)
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
            vendev = "????:????"
            builtin = "NO"
            pcidebug = "??:??.?"
            bridged = "YES"
            try:
                ven = binascii.hexlify(binascii.unhexlify(ven[1:5])[::-1]).decode()
                dev = binascii.hexlify(binascii.unhexlify(dev[1:5])[::-1]).decode()
                vendev = "{}:{}".format(ven,dev)
            except Exception as e:
                print(e)
                pass
            if "built-in" in p_dict or "IOBuiltin" in p_dict:
                builtin = "YES"
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
            if p_dict.get("acpi-path"):
                bridged = "NO"
            dev_list.append("{} {} {} {} {} = {}".format(
                pcidebug.ljust(7),
                vendev.ljust(9),
                builtin.ljust(8),
                bridged.ljust(7),
                p.get("acpi_path","Unknown APCI Path"),
                p.get("device_path","Unknown Device Path")
            ))
        if not dev_list:
            # Nothing was returned - adjust output based on
            # whether or not we're searching
            if device_name is None:
                print("No PCI devices located!")
            else:
                print("No device matching '{}' was found!".format(device_name))
            exit(1)
        # Add the header and separator
        dev_header = "{} {} {} {} ACPI+DevicePaths".format(
            "PCIDBG".ljust(7),
            "VEN:DEV".ljust(9),
            "Built-In".ljust(8),
            "Bridged".ljust(7)
        )
        dev_list = [dev_header,"-"*len(dev_header)]+sorted(dev_list)
        print("\n".join(dev_list))

if __name__ == '__main__':
    # Setup the cli args
    parser = argparse.ArgumentParser(prog="CheckPCI.py", description="CheckPCI - a py script to list PCI device info from the IODeviceTree.")
    parser.add_argument("-f", "--find-name", help="find device paths for objects with the passed name from the IODeviceTree")
    parser.add_argument("-i", "--local-ioreg", help="path to local ioreg dump to leverage")
    args = parser.parse_args()
    # Create our object and run our main function
    a = CheckPCI()
    if args.local_ioreg:
        ioreg_path = a.u.check_path(args.local_ioreg)
        if not ioreg_path:
            print("'{}' does not exist!".format(args.local_ioreg))
            exit(1)
        elif not os.path.isfile(ioreg_path):
            print("'{}' is not a file!".format(args.local_ioreg))
            exit(1)
        # Try loading it
        try:
            with open(ioreg_path,"rb") as f:
                a.i.ioreg["IOService"] = f.read().decode(errors="ignore").split("\n")
        except Exception as e:
            print("Failed to read '{}': {}".format(args.local_ioreg,e))
            exit(1)
        print("Using local ioreg: {}".format(ioreg_path))
    a.main(device_name=args.find_name)
