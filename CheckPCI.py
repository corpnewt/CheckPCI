import os, sys, binascii, argparse
from Scripts import ioreg, run, utils

class CheckPCI:
    def __init__(self):
        self.u = utils.Utils("CheckPCI")
        # Verify running OS
        if not sys.platform.lower() == "darwin":
            self.u.head("Wrong OS!")
            print("")
            print("This script can only be run on macOS!")
            print("")
            self.u.grab("Press [enter] to exit...")
            exit(1)
        self.r = run.Run()
        self.i = ioreg.IOReg()
        self.log = ""
        self.ioreg = None

    def get_boot_args(self):
        # Attempts to pull the boot-args from nvram
        out = self.r.run({"args":["nvram","-p"]})
        for l in out[0].split("\n"):
            if "boot-args" in l:
                return "\t".join(l.split("\t")[1:])
        return None

    def get_os_version(self):
        # Scrape sw_vers
        prod_name  = self.r.run({"args":["sw_vers","-productName"]})[0].strip()
        prod_vers  = self.r.run({"args":["sw_vers","-productVersion"]})[0].strip()
        build_vers = self.r.run({"args":["sw_vers","-buildVersion"]})[0].strip()
        if build_vers: build_vers = "({})".format(build_vers)
        return " ".join([x for x in (prod_name,prod_vers,build_vers) if x])

    def lprint(self, message):
        print(message)
        self.log += message + "\n"

    def main(self, device_name=None):
        if device_name is not None and not isinstance(device_name,str):
            device_name = str(device_name)
        all_devs = self.i.get_all_devices()
        # Add the header and separator
        dev_list = [
            "{} {} {} {} ACPI+DevicePaths".format(
                "PCIDBG".ljust(7),
                "VEN/DEV".ljust(9),
                "Built-In".ljust(8),
                "Bridged".ljust(7)
            )
        ]
        dev_list.append("-"*len(dev_list[0]))
        for p in sorted(all_devs.values(),key=lambda x:x.get("device_path")):
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
            if "built-in" in p_dict or "IOBuiltIn" in p_dict:
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
        if len(dev_list) == 2:
            # Nothing was returned - adjust output based on
            # whether or not we're searching
            if device_name is None:
                print("No PCI devices located!")
            else:
                print("No device matching '{}' was found!".format(device_name))
            exit(1)
        print("\n".join(dev_list))

if __name__ == '__main__':
    # Setup the cli args
    parser = argparse.ArgumentParser(prog="CheckPCI.py", description="CheckPCI - a py script to list PCI device info from the IODeviceTree.")
    parser.add_argument("-f", "--find-name", help="find device paths for objects with the passed name from the IODeviceTree")
    args = parser.parse_args()
    # Create our object and run our main function
    a = CheckPCI()
    a.main(device_name=args.find_name)