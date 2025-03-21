import os, sys, binascii, argparse, re
from Scripts import ioreg, utils, run

class CheckPCI:
    def __init__(self):
        # Verify running OS
        if not sys.platform.lower() == "darwin" and not os.name == "nt":
            print("This script can only be run on macOS or Windows!")
            exit(1)
        self.u = utils.Utils("CheckPCI")
        self.i = ioreg.IOReg()
        self.r = run.Run()
        if os.name == "nt":
            self.default_columns = [
                ("PCIDBG",7),
                ("VEN:DEV",9),
                ("Bridged",7),
                ("ACPI",0),
                ("Device",0)
            ]
        else:
            self.default_columns = (
                ("PCIDBG",7),
                ("VEN:DEV",9),
                ("Built-In",8),
                ("Bridged",7),
                ("ACPI",0),
                ("Device",0)
            )

    def hexy(self, integer,pad_to=0):
        return "0x"+hex(integer)[2:].upper().rjust(pad_to,"0")

    def sanitize_device_path(self, device_path):
        # Walk the device_path, gather the addresses, and rebuild it
        if not device_path or not device_path.lower().startswith("pciroot("):
            # Not a device path - bail
            return
        # Strip out PciRoot() and Pci() - then split by separators
        adrs = re.split(r"#|\/",device_path.lower().replace("pciroot(","").replace("pci(","").replace(")",""))
        new_path = []
        overflow_path = []
        for i,adr in enumerate(adrs):
            if i == 0:
                # Check for roots
                if "," in adr: return # Broken
                try:
                    adr = int(adr,16)
                    new_path.append("PciRoot({})".format(self.hexy(adr)))
                    overflow_path.append("PciRoot({})".format(self.hexy(0 if adr>0xFF else adr)))
                except: return # Broken again :(
            else:
                if "," in adr: # Not Windows formatted
                    try: adr1,adr2 = [int(x,16) for x in adr.split(",")]
                    except: return # REEEEEEEEEE
                else:
                    try:
                        adr = int(adr,16)
                        adr2,adr1 = adr & 0xFF, adr >> 8 & 0xFF
                    except: return # AAAUUUGGGHHHHHHHH
                # Should have adr1 and adr2 - let's add them
                new_path.append("Pci({},{})".format(self.hexy(adr1),self.hexy(adr2)))
                overflow_path.append("Pci({},{})".format(
                    self.hexy(0 if adr1>0xFF else adr1),
                    self.hexy(0 if adr2>0xFF else adr2)
                ))
        return ("/".join(new_path),"/".join(overflow_path))

    def format_acpi_path(self, acpi_path):
        if not acpi_path or not acpi_path.lower().startswith("acpi("):
            return
        acpi_comps = []
        for a in acpi_path.upper().split("#"):
            if a.startswith("ACPI("):
                # Got an APCI entry - unwrap it
                acpi_comps.append(a.split("ACPI(")[1].split(")")[0])
            elif a.startswith("PCI("):
                # This is abridge - just take note
                acpi_comps.append("pci-bridge")
        if not all(len(x)<=4 or x=="pci-bridge" for x in acpi_comps):
            # Broken somehow?
            return
        # Return the resulting path
        return ".".join(acpi_comps)

    def get_pci_dict(self):
        # Attempt to run a powershell one-liner to get a list of all
        # instance ids which start with PCI
        out = self.r.run({
            "args":[
                "powershell",
                "-c",
                "$devList=Get-PnpDevice|select -Property FriendlyName,InstanceId;foreach($d in $devList){$n=$d.FriendlyName;$d=$d.InstanceId;if($d.StartsWith(\"PCI\\\")){$l=Get-PnpDeviceProperty -KeyName DEVPKEY_Device_LocationInfo,DEVPKEY_Device_LocationPaths -InstanceId $d|select -Property Data;Write-Output $n $d $l}}"
            ]
        })[0].replace("\r","").split("\n")
        if not out:
            return None
        # Walk the devices and their subsequent paths
        dev = name = None
        loc = "??:??.?"
        dev_dict = {}
        for l in out:
            if not l.replace("-","").replace("Data","").strip():
                continue # Skip empty lines and headers
            if l.startswith("PCI\\"):
                # Got a device
                dev = l
            elif l.startswith("{") and dev:
                # Got the location paths
                try:
                    paths = l.split("{")[1].split("}")[0].split(", ")
                    dev_path = next((p for p in paths if p.startswith("PCIROOT(")),None)
                    acpi_path = next((p for p in paths if p.startswith("ACPI(")),None)
                    bridged = "NO" if all(x.startswith("ACPI(") for x in acpi_path.split("#")) else "YES"
                    try: ven_id = dev.split("VEN_")[1][:4]
                    except: ven_id = "????"
                    try: dev_id = dev.split("DEV_")[1][:4]
                    except: dev_id = "????"
                    dev_name = None
                    if acpi_path.split("#")[-1].startswith("ACPI("):
                        dev_name = acpi_path.split("ACPI(")[-1].split(")")[0]
                    dev_paths = self.sanitize_device_path(dev_path)
                    if not dev_paths:
                        # Broken?
                        continue
                    acpi_formatted = self.format_acpi_path(acpi_path)
                    if not acpi_formatted:
                        continue
                    dev_dict[dev] = {
                        "pcidebug":loc,
                        "device_path":dev_paths[0],
                        "acpi_path":acpi_formatted,
                        "bridged":bridged,
                        "ven_dev":"{}:{}".format(ven_id,dev_id).lower()
                    }
                    if dev_name:
                        dev_dict[dev]["name"] = dev_name
                    if dev_paths[0] != dev_paths[1]:
                        dev_dict[dev]["overflow_device_path"] = dev_paths[1]
                    if name:
                        dev_dict[dev]["friendly_name"] = name
                except:
                    pass
                dev = name = None # Reset
                loc = "??:??.?"
            elif l.startswith("PCI bus "):
                # Get our location info organizec the same way gfxutil does
                try:
                    a,b,c = [x.split()[-1] for x in l.split(", ")]
                    loc = "{}:{}.{}".format(
                        hex(int(a))[2:].rjust(2,"0"),
                        hex(int(b))[2:].rjust(2,"0"),
                        hex(int(c))[2:]
                    )
                except:
                    pass
            else:
                # Got a friendly name
                name = l.strip()
        return dev_dict

    def get_ps_entries(self):
        all_devs = self.get_pci_dict()
        rows = []
        for p in all_devs.values():
            rows.append({
                "name":p.get("name",""),
                "row":(
                    p["pcidebug"],
                    p["ven_dev"],
                    p["bridged"],
                    p["acpi_path"],
                    p["device_path"],
                    p.get("friendly_name","")
                )
            })
        return rows

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

    def get_ioreg_entries(self):
        all_devs = self.i.get_all_devices()
        # Walk the entries and process them as needed - returning
        # the values expected, in order
        rows = []
        for p in all_devs.values():
            p_dict = p.get("info",{})
            ven = p_dict.get("vendor-id")
            dev = p_dict.get("device-id")
            if not (ven and dev):
                continue # Missing info - skip
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
            rows.append({
                "name":p.get("name_no_addr",""),
                "row":(pcidebug,vendev,builtin,bridged,acpi,device)
            })
        return rows

    def main(self,device_name=None,columns=None,column_match=None,include_names=False):
        if device_name is not None and not isinstance(device_name,str):
            device_name = str(device_name)
        if include_names:
            self.default_columns.append(("FriendlyName",0))
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
        # Get our device list based on our OS
        if os.name == "nt":
            rows = self.get_ps_entries()
            check_back = 3 # Look for ACPI, Device, "" on Windows
        else:
            rows = self.get_ioreg_entries()
            check_back = 2 # Look for ACPI and Device on macOS
        dev_list = []
        # Iterate those devices
        for r in rows:
            # Check our name if we are looking for one
            if device_name and not r.get("name","").lower() == device_name.lower():
                continue # Not our device name - skip
            row = r["row"]
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
                row if sys.platform.lower()=="darwin" or include_names else row[:-1],
                column_list=display_columns
            )
            if row[-check_back:] == r["row"][-check_back:]:
                # Special handler to join ACPI and Device paths
                # with " = "
                row = row[:-check_back]+[" = ".join(r["row"][-check_back:])]
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
        dev_header = " ".join(header_row)
        # Append " Paths" if the last entry was a path
        if "ACPI Device" in dev_header:
            dev_header = dev_header.replace("ACPI Device","APCI+Device Paths")
        else:
            dev_header = dev_header.replace("ACPI","ACPI Paths").replace("Device","Device Paths")
        dev_header = dev_header.replace("ACPI Device","ACPI+Device")
        dev_header = dev_header.replace("ACPI+Device","ACPI+Device Paths")
        dev_list = [dev_header,"-"*len(dev_header)]+sorted(dev_list)
        print("\n".join(dev_list))
        if os.name == "nt":
            # Pause to prevent the window from closing prematurely
            self.u.grab("\nPress [enter] to exit...")

if __name__ == '__main__':
    # Create our object to get values for the help output
    p = CheckPCI()
    available = ", ".join("{} - {}".format(i,x[0]) for i,x in enumerate(p.default_columns,start=1))
    # Setup the cli args
    parser = argparse.ArgumentParser(prog="CheckPCI.py", description="CheckPCI - a py script to list PCI device info from the IODeviceTree.")
    parser.add_argument("-f", "--find-name", help="find device paths for objects with the passed name from the IODeviceTree")
    if os.name == "nt":
        parser.add_argument("-n", "--include-names", help="include friendly names for devices where applicable (Windows only)",action="store_true")
    else:
        parser.add_argument("-i", "--local-ioreg", help="path to local ioreg dump to leverage (macOS Only)")
    parser.add_argument("-c", "--column-list", help="comma delimited list of numbers representing which columns to display.  Options are:\n{}".format(available))
    parser.add_argument("-m", "--column-match", help="match entry formatted as NUM=VAL.  e.g. To match all bridged devices: 4=YES",action="append",nargs="*")
    
    args = parser.parse_args()
    
    if sys.platform.lower() == "darwin" and args.local_ioreg:
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
    p.main(
        device_name=args.find_name,
        columns=columns,
        column_match=column_match,
        include_names=getattr(args,"include_names",False)
    )
