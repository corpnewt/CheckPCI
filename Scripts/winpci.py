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

# Not currently used
'''SetupDiGetDevicePropertyKeys = setupapi.SetupDiGetDevicePropertyKeys
SetupDiGetDevicePropertyKeys.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, LPVOID, DWORD, PDWORD, DWORD]
SetupDiGetDevicePropertyKeys.restype = BOOL'''

SetupDiGetDeviceRegistryProperty = ctypes.windll.setupapi.SetupDiGetDeviceRegistryPropertyA
SetupDiGetDeviceRegistryProperty.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, DWORD, PDWORD, PBYTE, DWORD, PDWORD]
SetupDiGetDeviceRegistryProperty.restype = BOOL

SetupDiGetDeviceProperty = setupapi.SetupDiGetDevicePropertyW
SetupDiGetDeviceProperty.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, DEVPROPKEY, ULONG_PTR, PBYTE, DWORD, PDWORD, DWORD]
SetupDiGetDeviceProperty.restype = BOOL

# SetupDiGetClassDevs constants
DIGCF_DEFAULT         =  0x00000001  
DIGCF_PRESENT         =  0x00000002
DIGCF_ALLCLASSES      =  0x00000004
DIGCF_PROFILE         =  0x00000008
DIGCF_DEVICEINTERFACE =  0x00000010
# Error constants
ERROR_INVALID_DATA        = 13
ERROR_INSUFFICIENT_BUFFER = 122
ERROR_NO_MORE_ITEMS       = 259
ERROR_ELEMENT_NOT_FOUND   = 1168
#
# Device Property GUIDs and keys can be found in the devpkey.h header file:
# https://github.com/tpn/winsdk-10/blob/master/Include/10.0.16299.0/shared/devpkey.h
#
# Device Property GUIDs
DEVPKEY_GUID = GUID(0xa45c254e, 0xdf1c, 0x4efd,
    (BYTE*8)(0x80, 0x20, 0x67, 0xd1, 0x46, 0xa8, 0x50, 0xe0))
DEVPKEY_REL_GUID = GUID(0x4340a6c5, 0x93fa, 0x4706,
    (BYTE*8)(0x97, 0x2c, 0x7b, 0x64, 0x80, 0x08, 0xa5, 0xa7))
DEVPCIKEY_GUID = GUID(0x3ab22e31, 0x8264, 0x4b4e,
    (BYTE*8)(0x9a, 0xf5, 0xa8, 0xd2, 0xd8, 0xe3, 0x3e, 0x62))
# Device Property Keys
DEVPKEY_Device_Parent        = DEVPROPKEY(fmtid=DEVPKEY_REL_GUID,pid=8)
DEVPKEY_NAME                 = DEVPROPKEY(fmtid=DEVPKEY_GUID,pid=2)
DEVPKEY_Device_LocationInfo  = DEVPROPKEY(fmtid=DEVPKEY_GUID,pid=15)
DEVPKEY_Device_Address       = DEVPROPKEY(fmtid=DEVPKEY_GUID,pid=30)
DEVPKEY_Device_LocationPaths = DEVPROPKEY(fmtid=DEVPKEY_GUID,pid=37)
# Device Property PCI Keys
DEVPKEY_PciDevice_BaseClass  = DEVPROPKEY(fmtid=DEVPCIKEY_GUID,pid=3)
DEVPKEY_PciDevice_SubClass   = DEVPROPKEY(fmtid=DEVPCIKEY_GUID,pid=4)
DEVPKEY_PciDevice_ProgIf     = DEVPROPKEY(fmtid=DEVPCIKEY_GUID,pid=5)
#
# SPDRP codes can be found in the SetupAPI.h header file:
# https://github.com/tpn/winsdk-10/blob/master/Include/10.0.16299.0/um/SetupAPI.h
#
# SPDRP Codes
SPDRP_DEVICEDESC                  = 0x00000000  # DeviceDesc R/W
SPDRP_HARDWAREID                  = 0x00000001  # HardwareID R/W
SPDRP_COMPATIBLEIDS               = 0x00000002  # CompatibleIDs R/W
SPDRP_UNUSED0                     = 0x00000003  # unused
SPDRP_SERVICE                     = 0x00000004  # Service R/W
SPDRP_UNUSED1                     = 0x00000005  # unused
SPDRP_UNUSED2                     = 0x00000006  # unused
SPDRP_CLASS                       = 0x00000007  # Class R--tied to ClassGUID
SPDRP_CLASSGUID                   = 0x00000008  # ClassGUID R/W
SPDRP_DRIVER                      = 0x00000009  # Driver R/W
SPDRP_CONFIGFLAGS                 = 0x0000000A  # ConfigFlags R/W
SPDRP_MFG                         = 0x0000000B  # Mfg R/W
SPDRP_FRIENDLYNAME                = 0x0000000C  # FriendlyName R/W
SPDRP_LOCATION_INFORMATION        = 0x0000000D  # LocationInformation R/W
SPDRP_PHYSICAL_DEVICE_OBJECT_NAME = 0x0000000E  # PhysicalDeviceObjectName R
SPDRP_CAPABILITIES                = 0x0000000F  # Capabilities R
SPDRP_UI_NUMBER                   = 0x00000010  # UiNumber R
SPDRP_UPPERFILTERS                = 0x00000011  # UpperFilters R/W
SPDRP_LOWERFILTERS                = 0x00000012  # LowerFilters R/W
SPDRP_BUSTYPEGUID                 = 0x00000013  # BusTypeGUID R
SPDRP_LEGACYBUSTYPE               = 0x00000014  # LegacyBusType R
SPDRP_BUSNUMBER                   = 0x00000015  # BusNumber R
SPDRP_ENUMERATOR_NAME             = 0x00000016  # Enumerator Name R
SPDRP_SECURITY                    = 0x00000017  # Security R/W, binary form
SPDRP_SECURITY_SDS                = 0x00000018  # Security W, SDS form
SPDRP_DEVTYPE                     = 0x00000019  # Device Type R/W
SPDRP_EXCLUSIVE                   = 0x0000001A  # Device is exclusive-access R/W
SPDRP_CHARACTERISTICS             = 0x0000001B  # Device Characteristics R/W
SPDRP_ADDRESS                     = 0x0000001C  # Device Address R
SPDRP_UI_NUMBER_DESC_FORMAT       = 0x0000001D  # UiNumberDescFormat R/W
SPDRP_DEVICE_POWER_DATA           = 0x0000001E  # Device Power Data R
SPDRP_REMOVAL_POLICY              = 0x0000001F  # Removal Policy R
SPDRP_REMOVAL_POLICY_HW_DEFAULT   = 0x00000020  # Hardware Removal Policy R
SPDRP_REMOVAL_POLICY_OVERRIDE     = 0x00000021  # Removal Policy Override RW
SPDRP_INSTALL_STATE               = 0x00000022  # Device Install State R
SPDRP_LOCATION_PATHS              = 0x00000023  # Device Location Paths R
SPDRP_BASE_CONTAINERID            = 0x00000024  # Base ContainerID R

SPDRP_MAXIMUM_PROPERTY            = 0x00000025  # Upper bound on ordinals

def parse_data(arr, reg_data_type):
    if reg_data_type in (7,-4,-3): # Number
        return ctypes.wintypes.DWORD.from_buffer(arr).value
    elif reg_data_type in (18, 8210, -1, -7): # String or String Array
        if reg_data_type >= 0:
            # Convert from char array to wchar_t array (halving size)
            WArrType = ctypes.wintypes.WCHAR * (arr._length_ // ctypes.sizeof(ctypes.wintypes.WCHAR))
            warr = WArrType.from_buffer(arr)   # @TODO - cfati: You should probably use MultiByteToWideChar or mbstowcs here.
            ret = str(warr[:len(warr)]).rstrip("\x00")
        else:
            ret = arr.raw.decode(errors="ignore").rstrip("\x00")
        if reg_data_type in (8210,-7): # String Array
            return ret.split("\x00")
        elif reg_data_type in (18,-1): # String
            return ret.replace("\x00","")
    else:
        # More types could be handled here;
        # just return the argument as-is though
        return arr

def get_property(d_list,did,spdrp_prop):
    dproptype = ULONG()
    required_size = ULONG()
    if not SetupDiGetDeviceRegistryProperty(d_list, ctypes.byref(did), spdrp_prop, ctypes.byref(dproptype), None, 0, ctypes.byref(required_size)):
        if ctypes.GetLastError() in (ERROR_ELEMENT_NOT_FOUND,ERROR_INVALID_DATA):
            # Didn't find it
            return None
        if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
            # Failed to get value
            raise ctypes.WinError()
        buffer = ctypes.create_string_buffer(required_size.value)
        if not SetupDiGetDeviceRegistryProperty(d_list, ctypes.byref(did), spdrp_prop, ctypes.byref(dproptype), ctypes.byref(buffer), required_size.value, None):
            raise ctypes.WinError()
        # Return the cleaned value
        # Invert the property type value to avoid
        # collisions with get_dev_property types
        return parse_data(buffer,-dproptype.value)
    return None

def get_dev_property(d_list,did,devpkey):
    dproptype = ULONG()
    required_size = ULONG()
    if not SetupDiGetDeviceProperty(d_list, ctypes.byref(did), devpkey, ctypes.byref(dproptype), None, 0, ctypes.byref(required_size), 0):
        if ctypes.GetLastError() == ERROR_ELEMENT_NOT_FOUND:
            # Didn't find it
            return None
        if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
            # Failed to get value
            raise ctypes.WinError()
        buffer = ctypes.create_string_buffer(required_size.value)
        if not SetupDiGetDeviceProperty(d_list, ctypes.byref(did), devpkey, ctypes.byref(dproptype), ctypes.byref(buffer), required_size.value, None, 0):
            raise ctypes.WinError()
        # Return the cleaned buffer
        return parse_data(buffer,dproptype.value)
    return None

def get_pci_devices():
    # KeyName, DEVPKEY, SPDRP equivalent fallback if any
    props = (
        ("DEVPKEY_Device_Parent",       DEVPKEY_Device_Parent,       None),
        ("DEVPKEY_NAME",                DEVPKEY_NAME,                SPDRP_DEVICEDESC),
        ("DEVPKEY_Device_LocationPaths",DEVPKEY_Device_LocationPaths,SPDRP_LOCATION_PATHS),
        ("DEVPKEY_PciDevice_BaseClass", DEVPKEY_PciDevice_BaseClass, None),
        ("DEVPKEY_PciDevice_SubClass",  DEVPKEY_PciDevice_SubClass,  None),
        ("DEVPKEY_PciDevice_ProgIf",    DEVPKEY_PciDevice_ProgIf,    None),
        ("DEVPKEY_Device_Address",      DEVPKEY_Device_Address,      SPDRP_ADDRESS),
        ("DEVPKEY_Device_LocationInfo", DEVPKEY_Device_LocationInfo, SPDRP_LOCATION_INFORMATION)
    )
    devices = []

    d_list = SetupDiGetClassDevs(None, None, None, DIGCF_ALLCLASSES|DIGCF_PRESENT)
    if d_list == 0xFFFFFFFFFFFFFFFF:
        raise Exception("Invalid handle")
    index = 0
    did = SP_DEVINFO_DATA()
    did.cbSize = ctypes.sizeof(did)
    while True:
        if not SetupDiEnumDeviceInfo(d_list, index, ctypes.byref(did)):
            if ctypes.GetLastError() != ERROR_NO_MORE_ITEMS:
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
            # Resolve the instance id
            instance_id = parse_data(buffer,-1)
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

        for k,p,f in props:
            prop = get_dev_property(d_list,did,p)
            if prop is None:
                if f is None:
                    continue
                # Fall back if we can
                prop = get_property(d_list,did,f)
                if prop is None:
                    continue
            if isinstance(prop,list):
                prop = "{{{}}}".format(", ".join(prop))
            devices.append("{} {} {}".format(instance_id,k,prop))
    
    if devices:
        devices = ["InstanceId KeyName Data"]+devices
    return "\n".join(devices)

if __name__ == "__main__":
    print(get_pci_devices())