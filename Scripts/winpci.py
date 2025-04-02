import ctypes, re, struct
from ctypes.wintypes import WORD, BYTE, LPVOID, HWND, DWORD

prop_check = re.compile(r"^{?(PCI|ACPI\\PNP0A0(3|8))\\[^\\]*")

def ValidHandle(value, func, arguments):
    if value == 0:
        raise ctypes.WinError()
    return value

NULL = 0
HDEVINFO = ctypes.c_void_p
BOOL = ctypes.c_int
PDWORD = ctypes.POINTER(DWORD)
PWCHAR = ctypes.c_wchar_p
ULONG = ctypes.c_ulong
ULONG_PTR = ctypes.POINTER(ULONG)
#~ PBYTE = ctypes.c_char_p
PBYTE = ctypes.c_void_p

class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', DWORD),
        ('Data2', WORD),
        ('Data3', WORD),
        ('Data4', BYTE*8),
    ]

class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('ClassGuid', GUID),
        ('DevInst', DWORD),
        ('Reserved', ULONG_PTR),
    ]

class DEVPROPKEY(ctypes.Structure):
    _fields_ = [
        ("fmtid", GUID),
        ("pid", ULONG)
    ]

PSP_DEVINFO_DATA = ctypes.POINTER(SP_DEVINFO_DATA)
PDEVPROPKEY = ctypes.POINTER(DEVPROPKEY)

setupapi = ctypes.windll.LoadLibrary("setupapi")

SetupDiGetClassDevs = setupapi.SetupDiGetClassDevsW
SetupDiGetClassDevs.argtypes = [LPVOID, PWCHAR, HWND, DWORD]
SetupDiGetClassDevs.restype = HDEVINFO
SetupDiGetClassDevs.errcheck = ValidHandle

SetupDiEnumDeviceInfo = setupapi.SetupDiEnumDeviceInfo
SetupDiEnumDeviceInfo.argtypes = [HDEVINFO, DWORD, PSP_DEVINFO_DATA]
SetupDiEnumDeviceInfo.restype = BOOL

SetupDiGetDeviceInstanceId = setupapi.SetupDiGetDeviceInstanceIdA
SetupDiGetDeviceInstanceId.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, PBYTE, DWORD, PDWORD]
SetupDiGetDeviceInstanceId.restype = BOOL

SetupDiGetDevicePropertyKeys = setupapi.SetupDiGetDevicePropertyKeys
SetupDiGetDevicePropertyKeys.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, LPVOID, DWORD, PDWORD, DWORD]
SetupDiGetDevicePropertyKeys.restype = BOOL

SetupDiGetDeviceRegistryProperty = ctypes.windll.setupapi.SetupDiGetDeviceRegistryPropertyA
SetupDiGetDeviceRegistryProperty.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, DWORD, PDWORD, PBYTE, DWORD, PDWORD]
SetupDiGetDeviceRegistryProperty.restype = BOOL

SetupDiGetDeviceProperty = setupapi.SetupDiGetDevicePropertyW
SetupDiGetDeviceProperty.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, DEVPROPKEY, ULONG_PTR, PBYTE, DWORD, PDWORD, DWORD]
SetupDiGetDeviceProperty.restype = BOOL

# Local constants used
DIGCF_DEFAULT         =  0x00000001  
DIGCF_PRESENT         =  0x00000002
DIGCF_ALLCLASSES      =  0x00000004
DIGCF_PROFILE         =  0x00000008
DIGCF_DEVICEINTERFACE =  0x00000010
# Expected error
ERROR_NO_MORE_ITEMS   = 259
ERROR_INSUFFICIENT_BUFFER = 122
ERROR_ELEMENT_NOT_FOUND = 1168
# Device Properties
DEVPKEY_GUID = GUID(0xa45c254e, 0xdf1c, 0x4efd,
    (BYTE*8)(0x80, 0x20, 0x67, 0xd1, 0x46, 0xa8, 0x50, 0xe0))
DEVPKEY_REL_GUID = GUID(0x4340a6c5, 0x93fa, 0x4706,
    (BYTE*8)(0x97, 0x2c, 0x7b, 0x64, 0x80, 0x08, 0xa5, 0xa7))
DEVPCIKEY_GUID = GUID(0x3ab22e31, 0x8264, 0x4b4e,
    (BYTE*8)(0x9a, 0xf5, 0xa8, 0xd2, 0xd8, 0xe3, 0x3e, 0x62))
# DEVPKEY_Device_Parent
DEVPKEY_Device_Parent        = DEVPROPKEY(fmtid=DEVPKEY_REL_GUID,pid=8)
DEVPKEY_NAME                 = DEVPROPKEY(fmtid=DEVPKEY_GUID,pid=2)
DEVPKEY_Device_LocationInfo  = DEVPROPKEY(fmtid=DEVPKEY_GUID,pid=15)
DEVPKEY_Device_Address       = DEVPROPKEY(fmtid=DEVPKEY_GUID,pid=30)
DEVPKEY_Device_LocationPaths = DEVPROPKEY(fmtid=DEVPKEY_GUID,pid=37)

DEVPKEY_PciDevice_BaseClass  = DEVPROPKEY(fmtid=DEVPCIKEY_GUID,pid=3)
DEVPKEY_PciDevice_SubClass   = DEVPROPKEY(fmtid=DEVPCIKEY_GUID,pid=4)
DEVPKEY_PciDevice_ProgIf     = DEVPROPKEY(fmtid=DEVPCIKEY_GUID,pid=5)

# SPDRP Names
SPDRP_DEVICEDESC                  = 0x00000000
SPDRP_HARDWAREID                  = 0x00000001
SPDRP_COMPATIBLEIDS               = 0x00000002
SPDRP_UNUSED0                     = 0x00000003
SPDRP_SERVICE                     = 0x00000004
SPDRP_UNUSED1                     = 0x00000005
SPDRP_UNUSED2                     = 0x00000006
SPDRP_CLASS                       = 0x00000007
SPDRP_CLASSGUID                   = 0x00000008
SPDRP_DRIVER                      = 0x00000009
SPDRP_CONFIGFLAGS                 = 0x0000000a
SPDRP_MFG                         = 0x0000000b
SPDRP_FRIENDLYNAME                = 0x0000000c
SPDRP_LOCATION_INFORMATION        = 0x0000000d
SPDRP_PHYSICAL_DEVICE_OBJECT_NAME = 0x0000000e
SPDRP_CAPABILITIES                = 0x0000000f
SPDRP_UI_NUMBER                   = 0x00000010
SPDRP_UPPERFILTERS                = 0x00000011
SPDRP_LOWERFILTERS                = 0x00000012
SPDRP_BUSTYPEGUID                 = 0x00000013
SPDRP_LEGACYBUSTYPE               = 0x00000014
SPDRP_BUSNUMBER                   = 0x00000015
SPDRP_ENUMERATOR_NAME             = 0x00000016
SPDRP_SECURITY                    = 0x00000017
SPDRP_SECURITY_SDS                = 0x00000018
SPDRP_DEVTYPE                     = 0x00000019
SPDRP_EXCLUSIVE                   = 0x0000001a
SPDRP_CHARACTERISTICS             = 0x0000001b
SPDRP_ADDRESS                     = 0x0000001c
SPDRP_UI_NUMBER_DESC_FORMAT       = 0x0000001d
SPDRP_DEVICE_POWER_DATA           = 0x0000001e
SPDRP_REMOVAL_POLICY              = 0x0000001f
SPDRP_REMOVAL_POLICY_HW_DEFAULT   = 0x00000020
SPDRP_REMOVAL_POLICY_OVERRIDE     = 0x00000021
SPDRP_INSTALL_STATE               = 0x00000022
SPDRP_LOCATION_PATHS              = 0x00000023
SPDRP_BASE_CONTAINERID            = 0x00000024
SPDRP_MAXIMUM_PROPERTY            = 0x00000025

def clean_buffer(buffer, step=1):
    # Every other char is a null char - skip those,
    # also replace any additional null chars with newlines
    try:
        if 2/3==0:
            buffer_stripped = "".join(["\n" if x == b"\x00" else x for x in buffer.raw[::step]]).strip()
        else:
            buffer_stripped = "".join(["\n" if x == 0 else chr(x & 0xFF) for x in buffer.raw[::step]]).strip()
    except:
        return
    # Depending on the null char ending count, we can adjust
    # how we handle this data
    if buffer_stripped.count("\n"):
        return "{"+"{}".format(", ".join([x for x in buffer_stripped.split("\n")]))+"}"
    return buffer_stripped

def get_property(d_list,did,spdrp_prop):
    required_size = ULONG()
    if not SetupDiGetDeviceRegistryProperty(d_list, ctypes.byref(did), spdrp_prop, None, None, 0, ctypes.byref(required_size)):
        if ctypes.GetLastError() == ERROR_ELEMENT_NOT_FOUND:
            # Didn't find it
            return None
        if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
            # Failed to get value
            raise ctypes.WinError()
        buffer = ctypes.create_string_buffer(required_size.value)
        if not SetupDiGetDeviceRegistryProperty(d_list, ctypes.byref(did), spdrp_prop, None, ctypes.byref(buffer), required_size.value, None):
            raise ctypes.WinError()
        # Return the cleaned buffer
        return clean_buffer(buffer)
    return None

def get_dev_property(d_list,did,devpkey,skip_clean=False):
    dproptype = ULONG()
    required_size = ULONG()
    if not SetupDiGetDeviceProperty(d_list, ctypes.byref(did), devpkey, ctypes.byref(dproptype), None, 0, ctypes.byref(required_size), 0):
        if ctypes.GetLastError() == ERROR_ELEMENT_NOT_FOUND:
            # Didn't find it
            return None
        if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
            # Failed to get value
            raise ctypes.WinError()
        # buffer = (BYTE * required_size.value)()
        buffer = ctypes.create_string_buffer(required_size.value)
        if not SetupDiGetDeviceProperty(d_list, ctypes.byref(did), devpkey, ctypes.byref(dproptype), ctypes.byref(buffer), required_size.value, None, 0):
            raise ctypes.WinError()
        # Return the cleaned buffer
        if skip_clean:
            return buffer
        return clean_buffer(buffer,step=2)
    return None

def get_pci_devices():
    props = (
        (False, DEVPKEY_Device_Parent,       "DEVPKEY_Device_Parent"),
        (False, DEVPKEY_NAME,                "DEVPKEY_NAME"),
        (False, DEVPKEY_Device_LocationPaths,"DEVPKEY_Device_LocationPaths"),
        (True,  DEVPKEY_PciDevice_BaseClass, "DEVPKEY_PciDevice_BaseClass"),
        (True,  DEVPKEY_PciDevice_SubClass,  "DEVPKEY_PciDevice_SubClass"),
        (True,  DEVPKEY_PciDevice_ProgIf,    "DEVPKEY_PciDevice_ProgIf"),
        (True,  DEVPKEY_Device_Address,      "DEVPKEY_Device_Address"),
        (False, DEVPKEY_Device_LocationInfo, "DEVPKEY_Device_LocationInfo")
    )
    devices = []

    d_list = SetupDiGetClassDevs(None, None, None, DIGCF_ALLCLASSES|DIGCF_PRESENT)
    if d_list == 0xFFFFFFFFFFFFFFFF:
        raise Exception("Invalid handle")
    # Print the headers
    index = 0
    did = SP_DEVINFO_DATA()
    did.cbSize = ctypes.sizeof(did)
    while True:
        if not SetupDiEnumDeviceInfo(d_list, index, ctypes.byref(did)):
            if ctypes.GetLastError() != ERROR_NO_MORE_ITEMS:
                # print(ctypes.GetLastError())
                raise ctypes.WinError()
            break
        index += 1

        # Get our device instance id
        required_size = ULONG()
        instance_id = None
        if not SetupDiGetDeviceInstanceId(d_list, ctypes.byref(did), None, 0, ctypes.byref(required_size)):
            if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
                # Failed to get value
                raise ctypes.WinError()
            buffer = ctypes.create_string_buffer(required_size.value)
            if not SetupDiGetDeviceInstanceId(d_list, ctypes.byref(did), ctypes.byref(buffer), required_size.value, None):
                raise ctypes.WinError()
                continue
            # Return the cleaned buffer
            instance_id = clean_buffer(buffer)
        if not instance_id or not prop_check.match(instance_id):
            continue

        '''# Get our keys
        required_size = ULONG()
        devpkeys = None
        if not SetupDiGetDevicePropertyKeys(d_list, ctypes.byref(did), None, 0, ctypes.byref(required_size), 0):
            if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
                # Failed to get keys
                raise ctypes.WinError()
            devpkeys = (DEVPROPKEY * required_size.value)()
            if not SetupDiGetDevicePropertyKeys(d_list, ctypes.byref(did), ctypes.byref(devpkeys), required_size.value, None, 0):
                raise ctypes.WinError()'''

        for s,p,n in props:
            prop = get_dev_property(d_list,did,p,skip_clean=s)
            if not prop: continue
            if s:
                # Skipped cleaning - convert to an integer
                prop = struct.unpack_from("H",prop)[0]
            devices.append("{} {} {}".format(instance_id,n,prop))
    if devices:
        devices = ["InstanceId KeyName Data"]+devices
    return "\n".join(devices)

if __name__ == "__main__":
    print(get_pci_devices())