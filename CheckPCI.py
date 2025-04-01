import os, sys, binascii, argparse, re
from Scripts import ioreg, utils, run, plist

class CheckPCI:
    def __init__(self):
        # Verify running OS
        if not sys.platform.lower() == "darwin" and not os.name == "nt":
            print("This script can only be run on macOS or Windows!")
            exit(1)
        self.u = utils.Utils("CheckPCI")
        self.i = ioreg.IOReg()
        self.r = run.Run()
        self.b_d_f_re = re.compile(r"^[^\d]*(?P<bus>\d+)[^\d]+(?P<device>\d+)[^\d]+(?P<function>\d+)[^\d]*$")
        self.default_columns = [
            ("PCIDBG",7),
            ("VEN:DEV",9),
            ("Built-In",8),
            ("ACPI",0),
            ("Device",0)
        ]

    def hexy(self, integer,pad_to=0):
        return "0x"+hex(integer)[2:].upper().rjust(pad_to,"0")

    def sanitize_device_path(self, device_path):
        # Walk the device_path, gather the addresses, and rebuild it
        if not device_path or not device_path.lower().startswith("pciroot("):
            # Not a device path - bail
            return
        # Strip out PciRoot() and Pci() - then split by separators
        addrs = re.split(r"#|\/",device_path.lower().replace("pciroot(","").replace("pci(","").replace(")",""))
        new_path = []
        overflow_path = []
        for i,addr in enumerate(addrs):
            if i == 0:
                # Check for roots
                if "," in addr: return # Broken
                try:
                    addr = int(addr,16)
                    new_path.append("PciRoot({})".format(self.hexy(addr)))
                    overflow_path.append("PciRoot({})".format(self.hexy(0 if addr>0xFF else addr)))
                except: return # Broken again :(
            else:
                if "," in addr: # Not Windows formatted
                    try: addr1,addr2 = [int(x,16) for x in addr.split(",")]
                    except: return # REEEEEEEEEE
                else:
                    try:
                        addr = int(addr,16)
                        addr1,addr2 = addr >> 8 & 0xFF, addr & 0xFF
                    except: return # AAAUUUGGGHHHHHHHH
                # Should have addr1 and addr2 - let's add them
                new_path.append("Pci({},{})".format(self.hexy(addr1),self.hexy(addr2)))
                overflow_path.append("Pci({},{})".format(
                    self.hexy(0 if addr1>0xFF else addr1),
                    self.hexy(0 if addr2>0xFF else addr2)
                ))
        return ("/".join(new_path),"/".join(overflow_path))

    def get_acpi_from_pci(self,pci_element):
        if not isinstance(pci_element,str) or not pci_element.lower().startswith(("pci(","pciroot(")):
            return
        addr = pci_element.split("(")[1].split(")")[0]
        if pci_element.lower().startswith("pciroot("):
            # PCIROOT() entry
            return addr # Return as-is
        else:
            # PCI() entry
            try:
                addr = int(addr,16)
                addr1,addr2 = addr >> 8 & 0xFF, addr & 0xFF
            except:
                return
            # Build our address as needed
            if not addr2:
                return hex(addr1)[2:].upper()
            else:
                return "{},{}".format(
                    hex(addr1)[2:].upper(),
                    hex(addr2)[2:].upper()
                )

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
        if not all(len(x)<=4 or x.startswith("pci-bridge") for x in acpi_comps):
            # Broken somehow?
            return
        # Return the resulting path
        return ".".join(acpi_comps)

    def get_local_info(self):
        if os.name == "nt":
            return self.r.run({
                "args":[
                    "powershell",
                    "-c",
                    r"Get-PnpDevice -PresentOnly|Where-Object InstanceId -Match '^(PCI\\.*|ACPI\\PNP0A0(3|8)\\[^\\]*)'|Get-PnpDeviceProperty -KeyName DEVPKEY_Device_Parent,DEVPKEY_NAME,DEVPKEY_Device_LocationPaths,DEVPKEY_PciDevice_BaseClass,DEVPKEY_PciDevice_SubClass,DEVPKEY_PciDevice_ProgIf,DEVPKEY_Device_Address,DEVPKEY_Device_LocationInfo|Select -Property InstanceId,KeyName,Data|Format-Table -Autosize|Out-String -width 9999"
                ]
            })[0].replace("\r","").strip().split("\n")
        else:
            return self.i.get_ioreg(plane="IODeviceTree")

    def get_pci_dict(self, ps_output=None):
        # Attempt to run a powershell one-liner to get a list of all
        # instance ids which start with PCI
        if ps_output is None:
            # We didn't get a value sent
            ps_output = self.get_local_info()
        if not ps_output:
            return None
        # Walk the devices and their subsequent paths
        dev = None
        dev_dict = {}
        pci_dict = {}
        for l in ps_output:
            if not l.strip().startswith(("PCI\\","ACPI\\")):
                continue # No data here
            dev = l.split()[0].upper().strip()
            key = l.split()[1].strip()
            val = " ".join(l.split()[2:]).strip()
            if dev.startswith("ACPI\\"):
                # Got a PCI bus or root complex
                if not dev in pci_dict:
                    pci_dict[dev] = {}
                # See if we got a path - or an address
                if val.startswith("{"):
                    # ACPI address - get the path
                    try:
                        pci_dict[dev]["acpi_path"] = val.split("(")[-1].split(")")[0]
                    except:
                        pass
                else:
                    # Try to convert it to a number - assume it's an address
                    try:
                        pci_dict[dev]["address"] = hex(int(val.strip()))[2:].upper()
                    except:
                        # Not an int - skip it
                        continue
                # Check if we have both the acpi_path and address, and
                # ensure the path reflects that
                if all(x in pci_dict[dev] for x in ("acpi_path","address")) \
                and not "@" in pci_dict[dev]["acpi_path"]:
                    pci_dict[dev]["acpi_path"]+="@"+pci_dict[dev]["address"]
                continue # Skip PCI checks
            # We must have a PCI entry
            if not dev in dev_dict:
                # Initialize the device if needed
                dev_dict[dev] = {}
            if key == "DEVPKEY_Device_LocationPaths":
                # Got the location paths
                try:
                    paths = val.split("{")[1].split("}")[0].split(", ")
                    dev_path = next((p for p in paths if p.startswith("PCIROOT(")),None)
                    acpi_path = next((p for p in paths if p.startswith("ACPI(")),None)
                    built_in = "YES" if all(x.startswith("ACPI(") for x in acpi_path.split("#")) else "NO"
                    try: ven_id = dev.split("VEN_")[1][:4].lower()
                    except: ven_id = "????"
                    try: dev_dict[dev]["vendor-id"] = int(ven_id,16)
                    except: pass
                    try: dev_id = dev.split("DEV_")[1][:4].lower()
                    except: dev_id = "????"
                    try: dev_dict[dev]["device-id"] = int(dev_id,16)
                    except: pass
                    try:
                        subvensys_id = dev.split("SUBSYS_")[1][:8].lower()
                        dev_dict[dev]["subsystem-vendor-id"] = int(subvensys_id[:4],16)
                        dev_dict[dev]["subsystem-id"] = int(subvensys_id[4:],16)
                    except:
                        pass
                    dev_name = None
                    if acpi_path.split("#")[-1].startswith("ACPI("):
                        dev_name = acpi_path.split("ACPI(")[-1].split(")")[0].rstrip("_")
                    dev_paths = self.sanitize_device_path(dev_path)
                    if not dev_paths:
                        dev_paths = ("Unknown Device Path","Unknown Device Path")
                    acpi_formatted = self.format_acpi_path(acpi_path)
                    # Let's reformat the ACPI path - if any, skip the 
                    # first entry as it isn't considered in gfxutil (i.e. _SB)
                    if acpi_formatted:
                        # Make sure to prefix our path with /
                        acpi_parts = [a.rstrip("_") for a in acpi_formatted.split(".")[1:]]
                        # Get our addresses from the PCI() elements
                        pci_parts = dev_path.split("#")
                        if len(pci_parts) == len(acpi_parts):
                            # Walk the pci parts and keep track of the addressing
                            for i,part in enumerate(pci_parts):
                                addr = self.get_acpi_from_pci(part)
                                if not addr:
                                    continue
                                acpi_parts[i]+="@{}".format(addr)
                        if acpi_parts[-1].startswith("pci-bridge@"):
                            # We're a PCI bridge - save our ven,dev as well
                            pci_bridge = "pci{},{}@{}".format(
                                ven_id,
                                dev_id,
                                acpi_parts[-1].split("@")[-1]
                            )
                            acpi_parts = acpi_parts[:-1]+[pci_bridge]
                            dev_dict[dev]["pci_bridge"] = pci_bridge
                        acpi_formatted = "/"+"/".join(acpi_parts)
                    dev_dict[dev]["device_path"] = dev_paths[0]
                    dev_dict[dev]["acpi_path"] = acpi_formatted or "Unknown ACPI Path"
                    dev_dict[dev]["built_in"] = built_in
                    dev_dict[dev]["ven_dev"] = "{}:{}".format(ven_id,dev_id)
                    if dev_name:
                        dev_dict[dev]["name"] = dev_name
                    if dev_paths[0] != dev_paths[1]:
                        dev_dict[dev]["overflow_device_path"] = dev_paths[1]
                except:
                    pass
                dev = None # Reset
            elif key == "DEVPKEY_Device_Parent":
                if val.startswith(("ACPI\\")):
                    # Must be the root parent path
                    try:
                        pci_root = "PciRoot(0x{})".format(hex(int(val.split("\\")[-1],16))[2:].upper())
                        dev_dict[dev]["pci_root"] = pci_root
                        dev_dict[dev]["pci_root_path"] = val.strip().upper()
                    except:
                        pass
                elif val.startswith("PCI\\"):
                    # Got a parent path - keep track for later
                    dev_dict[dev]["parent_path"] = val.upper()
            elif key == "DEVPKEY_Device_Address":
                # Got the address
                dev_dict[dev]["address"] = int(val)
            elif key == "DEVPKEY_Device_LocationInfo":
                # Gather our PCI bus, device, and function info.
                try:
                    m = self.b_d_f_re.match(val)
                    a,b,c = m.group("bus"),m.group("device"),m.group("function")
                    dev_dict[dev]["pcidebug"] = "{}:{}.{}".format(
                        hex(int(a))[2:].rjust(2,"0"),
                        hex(int(b))[2:].rjust(2,"0"),
                        hex(int(c))[2:]
                    )
                except:
                    pass
            elif key == "DEVPKEY_NAME":
                # Got the device name
                dev_dict[dev]["friendly_name"] = val.strip()
            elif key == "DEVPKEY_PciDevice_BaseClass":
                # Got the base class
                try: dev_dict[dev]["base-class"] = int(val.strip())
                except: continue
            elif key == "DEVPKEY_PciDevice_SubClass":
                # Got the sub class
                try: dev_dict[dev]["sub-class"] = int(val.strip())
                except: continue
            elif key == "DEVPKEY_PciDevice_ProgIf":
                # Got the programming interface
                try: dev_dict[dev]["programming-interface"] = int(val.strip())
                except: continue
                # Check if we got all our class info and build
                # our 32-bit int as needed
                c = dev_dict[dev].get("base-class")
                s = dev_dict[dev].get("sub-class")
                p = dev_dict[dev].get("programming-interface")
                if all(x is not None for x in (c,s,p)):
                    # Class code uses 0xAAAABBCC type formatting
                    cc = (c << 16) + (s << 8) + p
                    dev_dict[dev]["class-code"] = cc
        # Resolve all parents to their pci_root
        for dev in dev_dict:
            # Make sure we have a root path, an ACPI path, and that our
            # root path exists in and corresponds to a valid ACPI path
            # in the pci_dict
            if dev_dict[dev].get("pci_root_path") \
            and dev_dict[dev].get("acpi_path","").startswith("/") \
            and dev_dict[dev]["pci_root_path"] in pci_dict \
            and pci_dict[dev_dict[dev]["pci_root_path"]].get("acpi_path"):
                # Update the ACPI path to reflect the PCI root's address,
                # not the _UID
                a = dev_dict[dev]["acpi_path"].split("/")
                b = pci_dict[dev_dict[dev]["pci_root_path"]]["acpi_path"]
                if a[1] != b:
                    # Only update if we need to
                    a[1] = b
                    dev_dict[dev]["acpi_path"] = "/".join(a)
            # Check for parents that need resolving
            if not "parent_path" in dev_dict[dev]:
                continue # No need - skip
            # Let's resolve this to the top parent
            seen = []
            p = dev
            while True:
                # Check if we have another parent
                if not p in dev_dict:
                    # Found an orphan - just bail
                    break
                _p = dev_dict[p].get("parent_path")
                if _p:
                    if _p in seen:
                        # Cyclic?
                        break
                    # Save it for later
                    seen.append(_p)
                    # Keep going
                    p = _p
                    continue
                # We reached the top - check
                # for a pci_root
                if dev_dict[p].get("pci_root"):
                    # Let's update ours to match this
                    pci_root = dev_dict[p]["pci_root"]
                    dev_dict[dev]["pci_root"] = pci_root
                break
        # Ensure all elements have the correct pci_root
        for dev in dev_dict:
            pci_root = dev_dict[dev].get("pci_root","PciRoot(0x0)")
            dev_path = dev_dict[dev].get("device_path")
            if dev_path and dev_path.startswith("PciRoot(") and not \
            dev_path.startswith(pci_root):
                dev_dict[dev]["device_path"] = "/".join([pci_root]+dev_path.split("/")[1:])
        # Ensure all our pci@x,y entries that were populated with
        # ven/dev ids are updated to pciVEN,DEV@x,y formatting
        for dev in dev_dict:
            if not dev_dict[dev].get("pci_bridge") or not dev_dict[dev].get("device_path"):
                # This isn't bridged or is missing a device path,
                # we don't need to update
                continue
            dev_path = dev_dict[dev]["device_path"]
            # We got a bridged device - let's check for every
            # device which starts with the same device path, and
            # update the Nth entry of the ACPI path to reflect
            # our bridge.
            for d in dev_dict:
                if d == dev or dev_dict[d].get("built_in") == "YES" \
                or not dev_dict[d].get("device_path","").startswith(dev_path) \
                or not dev_dict[d].get("acpi_path") or dev_dict[d]["acpi_path"].startswith("Unknown "):
                    # Don't check ourselves or broken/unrelated entries
                    continue
                # Replace the Nth entry in the ACPI path with our
                # bridge
                n = dev_path.count("/")+1
                a = dev_dict[d]["acpi_path"].split("/")
                a[n] = dev_dict[dev]["pci_bridge"]
                dev_dict[d]["acpi_path"] = "/".join(a)
        # Return the info
        return dev_dict

    def get_ps_entries(self,include_names=False, ps_output=None):
        all_devs = self.get_pci_dict(ps_output=ps_output)
        rows = []
        for p in all_devs.values():
            rows.append({
                "name":p.get("name",""),
                "row":[
                    p.get("pcidebug","??:??.?"),
                    p.get("ven_dev","????:????"),
                    p.get("built_in","???"),
                    p.get("acpi_path","Unknown ACPI Path"),
                    p.get("device_path","Unknown Device Path")
                ],
                "dict":{
                    "info":p,
                    "device_path":p.get("device_path")
                }
            })
            if include_names:
                rows[-1]["row"].append(
                    p.get("friendly_name","")
                )
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
                    (row[i] or "").ljust(self.default_columns[i][1])
                )
        else:
            # Not valid numbers - just get all of the
            # applicable entries and pad them
            for i,x in enumerate(row):
                if i < def_len:
                    # In range - pad as needed
                    x = (x or "").ljust(self.default_columns[i][1])
                new_row.append(x)
        return new_row

    def get_ioreg_entries(self,include_names=False):
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
            if "built-in" in p_dict or "IOBuiltin" in p_dict or p_dict.get("acpi-path"):
                builtin = "YES"
            acpi = p.get("acpi_path","Unknown ACPI Path")
            device = p.get("device_path","Unknown Device Path")
            rows.append({
                "name":p.get("name_no_addr",""),
                "row":[pcidebug,vendev,builtin,acpi,device],
                "dict":p
            })
            if include_names:
                rows[-1]["row"].append(self.i.get_pci_device_name(p_dict))
        return rows

    def _load_ioreg(self, ioreg_override, include_names=False):
        # Change to this directory for relative pathing
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        # Resolve the path
        ioreg_path = self.u.check_path(ioreg_override)
        ioreg_type = "macOS ioreg dump"
        if not ioreg_path:
            print("'{}' does not exist!".format(ioreg_override))
            exit(1)
        elif not os.path.isfile(ioreg_path):
            print("'{}' is not a file!".format(ioreg_override))
            exit(1)
        # Try loading it
        try:
            with open(ioreg_path,"rb") as f:
                # Read the data, replace null chars,
                # decode to a string, strip whitespace,
                # replace carriage returns, and split
                # by newlines (yay)
                ioreg_data = f.read() \
                .replace(b"\x00",b"") \
                .decode(errors="ignore") \
                .strip() \
                .replace("\r","") \
                .split("\n")
            # Make sure we got *something*
            assert ioreg_data
            # We need to determine if this is a macOS or Windows file
            if ioreg_data[0].startswith("+-o "):
                # Likely a macOS ioreg dump
                self.i.ioreg["IOService"] = ioreg_data
                rows = self.get_ioreg_entries(include_names=include_names)
            elif ioreg_data[0].startswith("InstanceId"):
                ioreg_type = "Windows Powershell dump"
                # Likely a Windows powershell dump
                rows = self.get_ps_entries(include_names=include_names,ps_output=ioreg_data)
            else:
                # Unknown approach - just throw an error
                print(ioreg_data[0:3])
                raise Exception("Unknown ioreg type")
        except Exception as e:
            print("Failed to read '{}': {}".format(ioreg_override,e))
            exit(1)
        print("Using local {}: {}".format(ioreg_type,ioreg_path))
        return rows

    def save_plist(self,plist_path,ioreg_override=None):
        # Check if we got an ioreg override file path
        if ioreg_override is not None:
            rows = self._load_ioreg(ioreg_override)
        else:
            # Get our device list based on our OS
            if os.name == "nt":
                rows = self.get_ps_entries()
            else:
                rows = self.get_ioreg_entries()
        devices = {
            "DeviceProperties": {
                "Add":{}
            }
        }
        dev_props = devices["DeviceProperties"]["Add"]
        for r in rows:
            rd = r.get("dict",{})
            p = rd.get("device_path")
            d = rd.get("info")
            if not p or not d:
                continue # Borked
            d_info = self.i.get_device_info_from_pci_ids(d)
            if not d_info or not d_info.get("device"):
                continue # Didn't resolve
            # Add our info - we want AAPL,slot-name, model, and
            # device_type for PCI devices to populate
            try:
                root = int(p.split("PciRoot(")[1].split(")")[0],16)
                paths = []
                for i,x in enumerate(p.split("/")):
                    if x.startswith("Pci("):
                        a = [int(y,16) for y in x.split("Pci(")[1].split(")")[0].split(",")]
                        # Check if we're adding the first entry
                        if not paths:
                            # Prepend our root
                            a = [root]+a
                        # Join into a string with commas
                        paths.append(",".join([str(y) for y in a]))
                # Join the path components with slashes
                slot_name = "Internal@{}".format("/".join(paths))
            except:
                continue # Borked in some way
            # Ensure Intel display adapters are prefixed with
            # "Intel" for Intel Power Gadget
            model = d_info["device"]
            if (d_info.get("class") or "").startswith("Display ") \
            and (d_info.get("vendor") or "").startswith("Intel") \
            and not model.startswith("Intel"):
                model = "Intel "+model
            dev_props[p] = {
                "AAPL,slot-name":slot_name,
                "model":model,
                "device_type":d_info.get("subclass") or d_info.get("class") or "Unknown Type"
            }
            # Check for built-in and warn if not
            try:
                if r["row"][2] != "YES":
                    dev_props[p]["# WARNING - Not Built-in"]="Device properties may not take effect unless PCI bridges are defined in ACPI"
            except:
                pass
        with open(plist_path,"wb") as f:
            plist.dump(devices,f)

    def main(self,device_name=None,columns=None,column_match=None,include_names=False,ioreg_override=None):
        if device_name is not None and not isinstance(device_name,str):
            device_name = str(device_name)
        if include_names and not self.default_columns[-1][0] == "FriendlyName":
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
        # Keep track of how far back we need to look for
        # pathing entries
        check_back,check_rem = (-3,-1) if include_names else (-2,None)
        # Check if we got an ioreg override file path
        if ioreg_override is not None:
            rows = self._load_ioreg(ioreg_override,include_names=include_names)
        else:
            # Get our device list based on our OS
            if os.name == "nt":
                rows = self.get_ps_entries(include_names=include_names)
            else:
                rows = self.get_ioreg_entries(include_names=include_names)
        dev_list = []
        # Iterate those devices
        for r in rows:
            # Check our name if we are looking for one
            if device_name and not r.get("name","").lower() == device_name.lower():
                continue # Not our device name - skip
            # Ensure our columns match if needed
            if column_match:
                matched = True
                for c,v in column_match:
                    if c >= len(r["row"]) or r["row"][c].lower() != v:
                        # Out of range
                        matched = False
                        continue
                if not matched:
                    continue # No match
            # Parse the info based on our columns
            row = self.get_row(
                r["row"],
                column_list=display_columns
            )
            if row[check_back:check_rem] == r["row"][check_back:check_rem]:
                # Special handler to join ACPI and Device paths
                # with " = "
                row = row[:check_back]+[" = ".join(r["row"][check_back:check_rem])]
                if check_rem is not None:
                    # Append the remainder separated by spaces again
                    row += r["row"][check_rem:]
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
        # Append " Path" if the last entry was a path
        if "ACPI Device" in dev_header:
            dev_header = dev_header.replace("ACPI Device","APCI+Device Path")
        else:
            dev_header = dev_header.replace("ACPI","ACPI Path").replace("Device","Device Path")
        dev_header = dev_header.replace("ACPI Device","ACPI+Device")
        dev_header = dev_header.replace("ACPI+Device","ACPI+Device Path")
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
    parser.add_argument("-n", "--include-names", help="include friendly names for devices where applicable",action="store_true")
    parser.add_argument("-i", "--local-ioreg", help="path relative to this script for local ioreg/powershell to leverage")
    parser.add_argument("-c", "--column-list", help="comma delimited list of numbers representing which columns to display.  Options are:\n{}".format(available))
    parser.add_argument("-m", "--column-match", help="match entry formatted as NUM=VAL.  e.g. To match all devices that aren't built-in: -m 3=NO",action="append",nargs="*")
    parser.add_argument("-o", "--output-file", help="dump the current machine's ioreg/powershell info to the provided path relative to this script and exit")
    parser.add_argument("-p", "--save-plist", help="dump all detected PCI devices to the provided path relative to this script and exit")

    args = parser.parse_args()

    if args.output_file:
        # Change to this directory for relative pathing
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        # Just dumping output
        ioreg_type = "Windows Powershell dump" if os.name == "nt" else "macOS ioreg dump"
        # Ensure it uses the .txt extension
        if not args.output_file.lower().endswith(".txt"):
            args.output_file += ".txt"
        print("Gathering info...")
        out = p.get_local_info()
        try:
            with open(args.output_file,"wb") as f:
                f.write("\n".join(out).encode())
        except Exception as e:
            print("Failed to save: {}".format(e))
            exit(1)
        print("Saved {} to '{}'".format(ioreg_type,args.output_file))
        exit()

    if args.save_plist:
        # Change to this directory for relative pathing
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        # Ensure it uses the .plist extension
        if not args.save_plist.lower().endswith(".plist"):
            args.save_plist += ".plist"
        print("Gathering info...")
        # Dump our PCI devices to the passed file path
        try:
            p.save_plist(
                args.save_plist,
                ioreg_override=args.local_ioreg
            )
        except Exception as e:
            print("Failed to save: {}".format(e))
            exit(1)
        print("Saved plist data to '{}'".format(args.save_plist))
        exit()

    columns = None
    if args.column_list:
        # Ensure we have values that are valid
        columns = []
        _max = len(p.default_columns)
        if args.include_names:
            _max += 1 # Account for the name column
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
        if args.include_names:
            _max += 1 # Account for the name column
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
    find_name = None
    if args.find_name:
        find_name = args.find_name.strip().rstrip("_")
    p.main(
        device_name=find_name,
        columns=columns,
        column_match=column_match,
        include_names=args.include_names,
        ioreg_override=args.local_ioreg
    )
