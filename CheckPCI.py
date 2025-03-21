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

    def get_row(self, row, column_list=None):
        # Takes an interable row and compares with
        # the default_columns - using only the indices
        # in the column_list and padding as needed.
        if not isinstance(row,(list,tuple)):
            # Not an interable type we want
            return None
        def_len = len(self.default_columns)
        new_row = []
        if isinstance(column_list,(list,tuple)) and \
        all(isinstance(x,int) and 0<=x<def_len for x in column_list):
            # We got a list of valid numbers - let's use it
            for i in sorted(column_list):
                if i >= len(row):
                    continue # Out of range
                new_row.append(
                    row[i].ljust(self.default_columns[i][1])
                )
        else:
            # Not valid numbers - just get all of the
            # applicable entries and pad them
            for i,x in enumerate(row):
                if i < def_len:
                    # In range - pad as needed
                    x = x.ljust(self.default_columns[i][1])
                new_row.append(x)
        return new_row

    def main(self,device_name=None,columns=None,column_match=None):
        if device_name is not None and not isinstance(device_name,str):
            device_name = str(device_name)
        display_columns = []
        if isinstance(columns,(list,tuple)):
            for c in columns:
                try:
                    c = int(c)
                    self.default_columns[c]
                    if not c in display_columns:
                        display_columns.append(c)
                except:
                    pass
        else:
            display_columns = None
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
                except:
                    pass
            vendev = "????:????"
            try:
                # Swap endianness of each 16-bit value and format
                ven = binascii.hexlify(binascii.unhexlify(ven[1:5])[::-1]).decode()
                dev = binascii.hexlify(binascii.unhexlify(dev[1:5])[::-1]).decode()
                vendev = "{}:{}".format(ven,dev)
            except:
                pass
            builtin = "NO"
            if "built-in" in p_dict or "IOBuiltin" in p_dict:
                builtin = "YES"
            bridged = "YES"
            if p_dict.get("acpi-path"):
                bridged = "NO"
            acpi = p.get("acpi_path","Unknown APCI Path")
            device = p.get("device_path","Unknown Device Path")
            row = (pcidebug,vendev,builtin,bridged,acpi,device)
            # Ensure our columns match if needed
            if column_match:
                matched = True
                for c,v in column_match:
                    if c >= len(row) or row[c].lower() != v:
                        # Out of range
                        matched = False
                        continue
                if not matched:
                    continue # No match
            # Parse the info based on our columns
            row = self.get_row(
                row,
                column_list=display_columns
            )
            if row[-2:] == [acpi,device]:
                # Special handler to join ACPI and Device paths
                # with " = "
                row = row[:-2]+[" = ".join([acpi,device])]
            # Add to the list
            dev_list.append(" ".join(row))
        if not dev_list:
            # Nothing was returned - adjust output based on
            # whether or not we're searching
            if device_name is None and column_match is None:
                print("No PCI devices located!")
            elif column_match:
                print("No devices matching the passed info were found!")
            else:
                print("No device matching '{}' was found!".format(device_name))
            exit(1)
        # Gather our column headers
        header_row = self.get_row(
            [x[0] for x in self.default_columns],
            column_list=display_columns
        )
        # Join "ACPI" and "Device" with a "+"
        if header_row[-2:] == ["ACPI","Device"]:
            header_row = header_row[:-2]+["ACPI+Device"]
        dev_header = " ".join(header_row)
        # Append " Paths" if the last entry was a path
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
    parser.add_argument("-m", "--column-match", help="match entry formatted as NUM=VAL.  e.g. To match all bridged devices: 4=YES",action="append",nargs="*")
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
                            columns.append(c-1)
                else:
                    c = int(x.strip())
                    assert 0 < c <= _max
                    if not c in columns:
                        columns.append(c-1)
            except:
                columns = None
                break
        if not columns:
            print("Invalid column information passed.  Can only accept comma delmited numbers from")
            print("1-{} corresponding to the following:".format(_max))
            print(available)
            exit(1)
    column_match = None
    if args.column_match:
        column_match = []
        _max = len(p.default_columns)
        for x in args.column_match:
            # Args are passed as individual lists
            for y in x:
                try:
                    c,m = y.split("=")
                    c = int(c.strip())
                    assert 0 < c <= _max
                    m = m.strip().lower() # Normalize case
                    # Strip any duplicate indices
                    column_match = [z for z in column_match if x[0] != c]
                    # Add our new check
                    column_match.append((c-1,m))
                except:
                    column_match = None
                    break
            if column_match is None:
                break # Ran into an issue
        if not column_match:
            print("Invalid column match information passed.")
            exit(1)
    p.main(device_name=args.find_name,columns=columns,column_match=column_match)
