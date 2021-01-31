#!/usr/bin/env python3
# !/usr/bin/env python3
# MTK Flash Client (c) B.Kerler 2020.
# Licensed under MIT License
"""
Usage:
    mtk.py -h | --help
    mtk.py [--vid=vid] [--pid=pid]
    mtk.py [--loader=filename]
    mtk.py [--debugmode]
    mtk.py [--gpt-num-part-entries=number] [--gpt-part-entry-size=number] [--gpt-part-entry-start-lba=number]
    mtk.py [--sectorsize=bytes]
    mtk.py printgpt [--memory=memtype] [--lun=lun] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid]
    mtk.py gpt <filename> [--memory=memtype] [--lun=lun] [--genxml] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid]
    mtk.py r <partitionname> <filename> [--memory=memtype] [--lun=lun] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid]
    mtk.py rl <directory> [--memory=memtype] [--lun=lun] [--skip=partnames] [--genxml] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid]
    mtk.py rf <filename> [--memory=memtype] [--lun=lun] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid]
    mtk.py rs <start_sector> <sectors> <filename> [--lun=lun] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid]
    mtk.py footer <filename> [--memory=memtype] [--lun=lun] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid]
    mtk.py reset [--debugmode] [--vid=vid] [--pid=pid]
    mtk.py dumpbrom [--filename=filename] [--ptype=ptype] [--wdt=wdt] [--var0=var0] [--var1=var1] [--da_addr=addr] [--brom_addr=addr] [--uartaddr=addr] [--debugmode] [--vid=vid] [--pid=pid] [--interface=interface]
    mtk.py payload <filename> [--var0=var0] [--var1=var1] [--wdt=wdt] [--uartaddr=addr] [--da_addr=addr] [--brom_addr=addr] [--debugmode] [--vid=vid] [--pid=pid] [--interface=interface]
    mtk.py crash [--debugmode] [--vid=vid] [--pid=pid]
    mtk.py gettargetconfig [--debugmode] [--vid=vid] [--pid=pid]

Description:
    printgpt [--memory=memtype] [--lun=lun]                                      # Print GPT Table information
    gpt <directory> [--memory=memtype] [--lun=lun]                               # Save gpt table to given directory
    r <partitionname> <filename> [--memory=memtype] [--lun=lun]                  # Read flash to filename
    rl <directory> [--memory=memtype] [--lun=lun] [--skip=partname]              # Read all partitions from flash to a directory
    rf <filename> [--memory=memtype] [--lun=lun]                                 # Read whole flash to file
    rs <start_sector> <sectors> <filename> [--lun=lun]                           # Read sectors starting at start_sector to filename
    footer <filename> [--memory=memtype] [--lun=lun]                             # Read crypto footer from flash
    reset                                                                        # Send mtk reset command
    dumpbrom [--wdt=wdt] [--var0=var0] [--val_1=val_1] [--payload_addr=addr]   # Try to dump the bootrom
    crash [--debugmode] [--vid=vid] [--pid=pid]                                  # Try to crash the preloader
    gettargetconfig [--debugmode] [--vid=vid] [--pid=pid]                        # Get target config (sbc, daa, etc.)
    payload <filename>                                                           # Run a specific kamakiri / da payload


Options:
    --loader=filename                  Use specific DA loader, disable autodetection [default: Loader/MTK_AllInOne_DA.bin]
    --vid=vid                          Set usb vendor id used for MTK Preloader [default: 0x0E8D]
    --pid=pid                          Set usb product id used for MTK Preloader [default: 0x2000]
    --sectorsize=bytes                 Set default sector size [default: 0x200]
    --debugmode                        Enable verbose mode
    --gpt-num-part-entries=number      Set GPT entry count [default: 0]
    --gpt-part-entry-size=number       Set GPT entry size [default: 0]
    --gpt-part-entry-start-lba=number  Set GPT entry start lba sector [default: 0]
    --skip=partnames                   Skip reading partition with names "partname1,partname2,etc."
    --wdt=wdt                          Set a specific watchdog addr
    --var0=var0                        Set kamakiri specific var0 value
    --var1=var1                        Set kamakiri specific var1 value
    --uart_addr=addr                   Set payload uart_addr value
    --da_addr=addr                     Set a specific da payload addr
    --brom_addr=addr                   Set a specific brom payload addr
    --ptype=ptype                      Set the payload type ("amonet","kamakiri")
    --uartaddr=addr                    Set the payload uart addr
"""

from docopt import docopt

args = docopt(__doc__, version='EDL 2.1')

def getint(value):
    if "0x" in value:
        return int(value, 16)
    else:
        return int(value, 10)

from enum import Enum
import usb.core
from Library.utils import *
from Library.usblib import usb_class
from Library.gpt import gpt
from struct import unpack, pack

logger = logging.getLogger(__name__)
import time

default_ids = [
    [0x0E8D, 0x0003, -1],
    [0x0E8D, 0x6000, 2],
    [0x0E8D, 0x2000, 3],
    [0x1004, 0x6000, 2],
]

hwcodetable = {
    0x321: "mt6735",
    0x335: "mt6737",
    0x699: "mt6739",
    0x717: "mt6761 Helio A22",
    0x6580: "mt6580",
    0x326: "mt6750 Helio P10",
    0x551: "mt6757 Helio P20",
    0x707: "mt6768",
    0x766: "mt6765",
    0x788: "mt6771",
    0x813: "mt6785",
    0x886: "mt6873 Dimensity 800 5G",
    0x8163: "mt8163",
    0x8172: "mt8173",
    0x8127: "mt8127"
}


class deviceclass:
    vid = 0
    pid = 0

    def __init__(self, vid, pid):
        self.vid = vid
        self.pid = pid


entry_region = [
    ('m_buf', 'I'),
    ('m_len', 'I'),
    ('m_start_addr', 'I'),
    ('m_start_offset', 'I'),
    ('m_sig_len', 'I')]

DA = [
    ('magic', 'H'),
    ('hw_code', 'H'),
    ('hw_sub_code', 'H'),
    ('hw_version', 'H'),
    ('sw_version', 'H'),
    ('reserved1', 'H'),
    ('pagesize', 'H'),
    ('reserved3', 'H'),
    ('entry_region_index', 'H'),
    ('entry_region_count', 'H')
    # vector<entry_region> LoadRegion
]

bldrinfo = [
    ('m_nor_ret', '>I'),
    ('m_nor_chip_select', '2B'),
    ('m_nor_flash_id', '>H'),
    ('m_nor_flash_size', '>I'),
    ('m_nor_flash_dev_code', '>4H'),
    ('m_nor_flash_otp_status', '>I'),
    ('m_nor_flash_otp_size', '>I'),

    ('m_nand_info', '>I'),
    ('m_nand_chip_select', '>B'),
    ('m_nand_flash_id', '>H'),
    ('m_nand_flash_size', '>Q'),
    ('m_nand_flash_id_count', '>H'),
    ('m_nand_flash_dev_code', '>7H'),
    ('m_nand_pagesize', '>H'),
    ('m_nand_sparesize', '>H'),
    ('m_nand_pages_per_block', '>H'),
    ('m_nand_io_interface', 'B'),
    ('m_nand_addr_cycle', 'B'),
    ('m_nand_bmt_exist', 'B'),
    ('m_emmc_ret', '>I'),
    ('m_emmc_boot1_size', '>Q'),
    ('m_emmc_boot2_size', '>Q'),
    ('m_emmc_rpmb_size', '>Q'),
    ('m_emmc_gp_size', '>4Q'),
    ('m_emmc_ua_size', '>Q'),
    ('m_emmc_cid', '>2Q'),
    ('m_emmc_fwver', '8B'),

    ('m_sdmmc_info', '>I'),
    ('m_sdmmc_ua_size', '>Q'),
    ('m_sdmmc_cid', '>2Q'),
    ('m_int_sram_ret', '>I'),
    ('m_int_sram_size', '>I'),
    ('m_ext_ram_ret', '>I'),
    ('m_ext_ram_type', 'B'),
    ('m_ext_ram_chip_select', 'B'),
    ('m_ext_ram_size', '>Q'),
    ('randomid', '>2Q'),
    ('ack', 'B'),
    ('m_download_status', '>I'),
    ('m_boot_style', '>I'),
    ('soc_ok', 'B')
]


def split_by_n(seq, unit_count):
    """A generator to divide a sequence into chunks of n units."""
    while seq:
        yield seq[:unit_count]
        seq = seq[unit_count:]


class GCPU:
    GCPU_REG_CTL = 0
    GCPU_REG_MSC = 4

    def __init__(self, hwcode):
        if hwcode in [0x321, 0x335]:
            self.cryptobase = 0x10216000  # mt6735, 6737, 6753, 6735m
        elif hwcode in [0x326]:
            self.cryptobase = 0x10210000  # mt6750
        elif hwcode in [0x5700]:  # Fix me
            self.cryptobase = 0xf0016000
        else:
            self.cryptobase = 0x10210000  # 6761, 6757, 6739, 6755, 6797

        self.GCPU_REG_PC_CTL = self.cryptobase + 0x400
        self.GCPU_REG_MEM_ADDR = self.cryptobase + 0x404
        self.GCPU_REG_MEM_DATA = self.cryptobase + 0x408

        self.GCPU_REG_MONCTL = self.cryptobase + 0x414

        self.GCPU_REG_DRAM_INST_BASE = self.cryptobase + 0x420

        self.GCPU_REG_TRAP_START = self.cryptobase + 0x440
        self.GCPU_REG_TRAP_END = self.cryptobase + 0x478

        self.GCPU_REG_INT_SET = self.cryptobase + 0x800
        self.GCPU_REG_INT_CLR = self.cryptobase + 0x804
        self.GCPU_REG_INT_EN = self.cryptobase + 0x808

        self.GCPU_REG_MEM_CMD = self.cryptobase + 0xC00
        self.GCPU_REG_MEM_P0 = self.cryptobase + 0xC04
        self.GCPU_REG_MEM_P1 = self.cryptobase + 0xC08
        self.GCPU_REG_MEM_P2 = self.cryptobase + 0xC0C
        self.GCPU_REG_MEM_P3 = self.cryptobase + 0xC10
        self.GCPU_REG_MEM_P4 = self.cryptobase + 0xC14
        self.GCPU_REG_MEM_P5 = self.cryptobase + 0xC18
        self.GCPU_REG_MEM_P6 = self.cryptobase + 0xC1C
        self.GCPU_REG_MEM_P7 = self.cryptobase + 0xC20
        self.GCPU_REG_MEM_P8 = self.cryptobase + 0xC24
        self.GCPU_REG_MEM_P9 = self.cryptobase + 0xC28
        self.GCPU_REG_MEM_P10 = self.cryptobase + 0xC2C
        self.GCPU_REG_MEM_P11 = self.cryptobase + 0xC30
        self.GCPU_REG_MEM_P12 = self.cryptobase + 0xC34
        self.GCPU_REG_MEM_P13 = self.cryptobase + 0xC38
        self.GCPU_REG_MEM_P14 = self.cryptobase + 0xC3C
        self.GCPU_REG_MEM_Slot = self.cryptobase + 0xC40


class Mtk(metaclass=LogBase):
    class mtktypes(Enum):
        M_EMMC = 1
        M_NAND = 2
        M_NOR = 3

    class mtkcmd(Enum):
        CMD_CHECK_USB_CMD = b"\x72"
        CMD_PWR_INIT = b"\xC4"
        CMD_PWR_DEINIT = b"\xC5"
        CMD_PWR_READ16 = b"\xC6"
        CMD_PWR_WRITE16 = b"\xC7"
        CMD_READ16 = b'\xD0'
        CMD_READ32 = b"\xD1"
        CMD_WRITE16 = b"\xD2"
        CMD_WRITE32 = b"\xD4"
        CMD_JUMP_DA = b'\xD5'
        CMD_SEND_DA = b'\xD7'
        CMD_GET_TARGET_CONFIG = b"\xD8"
        CMD_SEND_EPP = b'\xD9'
        CMD_UART1_LOG_EN = b'\xDB'

        CMD_GET_ME_ID = b'\xE1'
        CMD_GET_SOC_ID = b'\xE7'

        # if CFG_PRELOADER_AS_DA
        CMD_SEND_IMAGE = b'\x70'
        CMD_BOOT_IMAGE = b'\x71'

        CMD_GET_VERSION = b"\xff"
        CMD_GET_BL_VER = b"\xfe"
        CMD_GET_HW_SW_VER = b"\xfc"
        CMD_GET_HW_CODE = b"\xfd"

        NONE = b''
        CONF = b'\x69'
        STOP = b'\x96'
        ACK = b'\x5A'
        NACK = b'\xA5'

    class mtkdacmd(Enum):
        SOC_OK = b"\xC1"
        SOC_FAIL = b"\xCF"
        SYNC_CHAR = b"\xC0"
        CONT_CHAR = b"\x69"
        STOP_CHAR = b"\x96"
        ACK = b"\x5A"
        NACK = b"\xA5"
        UNKNOWN_CMD = b"\xBB"

        # COMMANDS
        DA_DOWNLOAD_BLOADER_CMD = b"\x51"
        DA_NAND_BMT_REMARK_CMD = b"\x52"

        DA_SDMMC_SWITCH_PART_CMD = b"\x60"
        DA_SDMMC_WRITE_IMAGE_CMD = b"\x61"
        DA_SDMMC_WRITE_DATA_CMD = b"\x62"
        DA_SDMMC_GET_CARD_TYPE = b"\x63"
        DA_SDMMC_RESET_DIS_CMD = b"\x64"

        DA_UFS_SWITCH_PART_CMD = b"\x80"
        DA_UFS_WRITE_IMAGE_CMD = b"\x81"
        DA_UFS_WRITE_DATA_CMD = b"\x82"
        DA_UFS_READ_GPT_CMD = b"\x85"
        DA_UFS_WRITE_GPT_CMD = b"\x89"

        DA_UFS_OTP_CHECKDEVICE_CMD = b"\x8a"
        DA_UFS_OTP_GETSIZE_CMD = b"\x8b"
        DA_UFS_OTP_READ_CMD = b"\x8c"
        DA_UFS_OTP_PROGRAM_CMD = b"\x8d"
        DA_UFS_OTP_LOCK_CMD = b"\x8e"
        DA_UFS_OTP_LOCK_CHECKSTATUS_CMD = b"\x8f"

        DA_USB_SETUP_PORT = b"\x70"
        DA_USB_LOOPBACK = b"\x71"
        DA_USB_CHECK_STATUS = b"\x72"
        DA_USB_SETUP_PORT_EX = b"\x73"

        # EFFUSE
        DA_READ_REG32_CMD = b"\x7A"
        DA_WRITE_REG32_CMD = b"\x7B"
        DA_PWR_READ16_CMD = b"\x7C"
        DA_PWR_WRITE16_CMD = b"\x7D"
        DA_PWR_READ8_CMD = b"\x7E"
        DA_PWR_WRITE8_CMD = b"\x7F"

        DA_EMMC_OTP_CHECKDEVICE_CMD = b"\x99"
        DA_EMMC_OTP_GETSIZE_CMD = b"\x9A"
        DA_EMMC_OTP_READ_CMD = b"\x9B"
        DA_EMMC_OTP_PROGRAM_CMD = b"\x9C"
        DA_EMMC_OTP_LOCK_CMD = b"\x9D"
        DA_EMMC_OTP_LOCK_CHECKSTATUS_CMD = b"\x9E"

        DA_WRITE_USB_DOWNLOAD_CONTROL_BIT_CMD = b"\xA0"
        DA_WRITE_PARTITION_TBL_CMD = b"\xA1"
        DA_READ_PARTITION_TBL_CMD = b"\xA2"
        DA_READ_BMT = b"\xA3"
        DA_SDMMC_WRITE_PMT_CMD = b"\xA4"
        DA_SDMMC_READ_PMT_CMD = b"\xA5"
        DA_READ_IMEI_PID_SWV_CMD = b"\xA6"
        DA_READ_DOWNLOAD_INFO = b"\xA7"
        DA_WRITE_DOWNLOAD_INFO = b"\xA8"
        DA_SDMMC_WRITE_GPT_CMD = b"\xA9"
        DA_NOR_READ_PTB_CMD = b"\xAA"
        DA_NOR_WRITE_PTB_CMD = b"\xAB"

        DA_NOR_BLOCK_INDEX_TO_ADDRESS = b"\xB0"  # deprecated
        DA_NOR_ADDRESS_TO_BLOCK_INDEX = b"\xB1"  # deprecated
        DA_NOR_WRITE_DATA = b"\xB2"  # deprecated
        DA_NAND_WRITE_DATA = b"\xB3"
        DA_SECURE_USB_RECHECK_CMD = b"\xB4"
        DA_SECURE_USB_DECRYPT_CMD = b"\xB5"
        DA_NFB_BL_FEATURE_CHECK_CMD = b"\xB6"  # deprecated
        DA_NOR_BL_FEATURE_CHECK_CMD = b"\xB7"  # deprecated

        DA_SF_WRITE_IMAGE_CMD = b"\xB8"  # deprecated

        # Android S-USBDL
        DA_SECURE_USB_IMG_INFO_CHECK_CMD = b"\xB9"
        DA_SECURE_USB_WRITE = b"\xBA"
        DA_SECURE_USB_ROM_INFO_UPDATE_CMD = b"\xBB"
        DA_SECURE_USB_GET_CUST_NAME_CMD = b"\xBC"
        DA_SECURE_USB_CHECK_BYPASS_CMD = b"\xBE"
        DA_SECURE_USB_GET_BL_SEC_VER_CMD = b"\xBF"
        # Android S-USBDL

        DA_VERIFY_IMG_CHKSUM_CMD = b"\xBD"

        DA_GET_BATTERY_VOLTAGE_CMD = b"\xD0"
        DA_POST_PROCESS = b"\xD1"
        DA_SPEED_CMD = b"\xD2"
        DA_MEM_CMD = b"\xD3"
        DA_FORMAT_CMD = b"\xD4"
        DA_WRITE_CMD = b"\xD5"
        DA_READ_CMD = b"\xD6"
        DA_WRITE_REG16_CMD = b"\xD7"
        DA_READ_REG16_CMD = b"\xD8"
        DA_FINISH_CMD = b"\xD9"
        DA_GET_DSP_VER_CMD = b"\xDA"
        DA_ENABLE_WATCHDOG_CMD = b"\xDB"
        DA_NFB_WRITE_BLOADER_CMD = b"\xDC"  # deprecated
        DA_NAND_IMAGE_LIST_CMD = b"\xDD"
        DA_NFB_WRITE_IMAGE_CMD = b"\xDE"
        DA_NAND_READPAGE_CMD = b"\xDF"
        DA_CHK_PC_SEC_INFO_CMD = b"\xE0"
        DA_UPDATE_FLASHTOOL_CFG_CMD = b"\xE1"
        DA_CUST_PARA_GET_INFO_CMD = b"\xE2"  # deprecated
        DA_CUST_PARA_READ_CMD = b"\xE3"  # deprecated
        DA_CUST_PARA_WRITE_CMD = b"\xE4"  # deprecated
        DA_SEC_RO_GET_INFO_CMD = b"\xE5"  # deprecated
        DA_SEC_RO_READ_CMD = b"\xE6"  # deprecated
        DA_SEC_RO_WRITE_CMD = b"\xE7"  # deprecated
        DA_ENABLE_DRAM = b"\xE8"
        DA_OTP_CHECKDEVICE_CMD = b"\xE9"
        DA_OTP_GETSIZE_CMD = b"\xEA"
        DA_OTP_READ_CMD = b"\xEB"
        DA_OTP_PROGRAM_CMD = b"\xEC"
        DA_OTP_LOCK_CMD = b"\xED"
        DA_OTP_LOCK_CHECKSTATUS_CMD = b"\xEE"
        DA_GET_PROJECT_ID_CMD = b"\xEF"
        DA_GET_FAT_INFO_CMD = b"\xF0"  # deprecated
        DA_FDM_MOUNTDEVICE_CMD = b"\xF1"
        DA_FDM_SHUTDOWN_CMD = b"\xF2"
        DA_FDM_READSECTORS_CMD = b"\xF3"
        DA_FDM_WRITESECTORS_CMD = b"\xF4"
        DA_FDM_MEDIACHANGED_CMD = b"\xF5"
        DA_FDM_DISCARDSECTORS_CMD = b"\xF6"
        DA_FDM_GETDISKGEOMETRY_CMD = b"\xF7"
        DA_FDM_LOWLEVELFORMAT_CMD = b"\xF8"
        DA_FDM_NONBLOCKWRITESECTORS_CMD = b"\xF9"
        DA_FDM_RECOVERABLEWRITESECTORS_CMD = b"\xFA"
        DA_FDM_RESUMESECTORSTATES = b"\xFB"
        DA_NAND_EXTRACT_NFB_CMD = b"\xFC"  # deprecated
        DA_NAND_INJECT_NFB_CMD = b"\xFD"  # deprecated

        DA_MEMORY_TEST_CMD = b"\xFE"
        DA_ENTER_RELAY_MODE_CMD = b"\xFF"

        UART_BAUD_921600 = b'\x01'
        UART_BAUD_460800 = b'\x02'
        UART_BAUD_230400 = b'\x03'
        UART_BAUD_115200 = b'\x04'

    def __init__(self, args, loader, loglevel=logging.INFO, vid=-1, pid=-1, interface=0, pagesize=512):
        filename = "log.txt"
        da_address = args["--da_addr"]
        if da_address == None:
            self.da_address = 0x200D00
        else:
            self.da_address = getint(da_address)
        brom_address = args["--brom_addr"]
        if brom_address == None:
            self.brom_address = 0x100A00
        else:
            self.brom_address = getint(da_address)
        watchdog_address = args["--wdt"]
        if watchdog_address == None:
            self.watchdog_addr = 0
        else:
            self.watchdog_addr = getint(watchdog_address)
        uart_address = args["--uartaddr"]
        if uart_address == None:
            self.uart_addr = 0x11002000
        else:
            self.uart_addr = getint(uart_address)
        if args["--var0"] == None:
            self.var_0 = None
        else:
            self.var_0 = getint(args["--var0"])
        if args["--var1"] == None:
            self.var_1 = 0xA
        else:
            self.var_1 = getint(args["--var1"])

        if vid != -1 and pid != -1:
            if interface == -1:
                for dev in default_ids:
                    if dev[0] == vid and dev[1] == pid:
                        interface = dev[2]
                        break
            portconfig = [[vid, pid, interface]]
        else:
            portconfig = default_ids
        if loglevel == logging.DEBUG:
            logfilename = "log.txt"
            if os.path.exists(logfilename):
                os.remove(logfilename)
            fh = logging.FileHandler(logfilename)
            self.__logger.addHandler(fh)
            self.__logger.setLevel(logging.DEBUG)
        else:
            self.__logger.setLevel(logging.INFO)
        self.cdc = usb_class(portconfig=portconfig, loglevel=loglevel)
        self.packetsizeread = 0x400
        self.flashinfo = None
        self.flashsize = 0
        self.readsize = 0
        self.sparesize = 16
        self.da = None
        self.gcpu = None
        self.pagesize = pagesize
        self.flash = "emmc"
        self.loader = loader
        if not os.path.exists(loader):
            self.__logger.error("Couldn't open " + loader)
            exit(0)

        self.da_setup = []
        with open(loader, 'rb') as bootldr:
            bootldr.seek(0x68)
            count_da = struct.unpack("<I", bootldr.read(4))[0]
            for i in range(0, count_da):
                bootldr.seek(0x6C + (i * 0xDC))
                datmp = read_object(bootldr.read(0x14), DA)  # hdr
                da = [datmp]
                # bootldr.seek(0x6C + (i * 0xDC) + 0x14) #sections
                for m in range(0, datmp["entry_region_count"]):
                    entry_tmp = read_object(bootldr.read(20), entry_region)
                    da.append(entry_tmp)
                self.da_setup.append(da)

    def usbwrite(self, data):
        size = self.cdc.write(data, len(data))
        # port->flush()
        return size

    def close(self):
        self.cdc.close()

    def usbreadwrite(self, data, resplen):
        size = self.usbwrite(data)
        # port->flush()
        res = self.usbread(resplen)
        return res

    def usbread(self, resplen):
        res = b""
        timeout = 0
        while (resplen > 0):
            tmp = self.cdc.read(resplen)
            if tmp == b"":
                if timeout == 4:
                    break
                timeout += 1
                time.sleep(0.1)
            resplen -= len(tmp)
            res += tmp
        return res

    def get_gpt(self, gpt_num_part_entries, gpt_part_entry_size, gpt_part_entry_start_lba):
        data = self.readflash(0, 2 * self.pagesize, "", False)
        if data == b"":
            return None, None
        guid_gpt = gpt(
            num_part_entries=gpt_num_part_entries,
            part_entry_size=gpt_part_entry_size,
            part_entry_start_lba=gpt_part_entry_start_lba,
        )
        header = guid_gpt.parseheader(data, self.pagesize)
        if "first_usable_lba" in header:
            sectors = header["first_usable_lba"]
            if sectors == 0:
                return None, None
            data = self.readflash(0, sectors * self.pagesize, "", False)
            if data == b"":
                return None, None
            guid_gpt.parse(data, self.pagesize)
            return data, guid_gpt
        else:
            return None, None

    def get_backup_gpt(self, lun, gpt_num_part_entries, gpt_part_entry_size, gpt_part_entry_start_lba):
        data = self.readflash(0, 2 * self.pagesize, "", False)
        if data == b"":
            return None
        guid_gpt = gpt(
            num_part_entries=gpt_num_part_entries,
            part_entry_size=gpt_part_entry_size,
            part_entry_start_lba=gpt_part_entry_start_lba,
        )
        header = guid_gpt.parseheader(data, self.cfg.SECTOR_SIZE_IN_BYTES)
        if "backup_lba" in header:
            sectors = header["first_usable_lba"] - 1
            data = self.readflash(header["backup_lba"] * self.pagesize, sectors * self.pagesize, "", False)
            if data == b"":
                return None
            return data
        else:
            return None

    def detect(self, loop=0):
        while not self.cdc.connected:
            self.cdc.connected = self.cdc.connect()
            if self.cdc.connected:
                startcmd = [b"\xa0", b"\x0a", b"\x50", b"\x05"]
                respcmd = b"\x5F\xF5\xAF\xFA"
                tries = 100
                i = 0
                length = len(startcmd)
                while i < length and tries > 0:
                    cmd = startcmd[i]
                    res = respcmd[i]
                    r = self.usbwrite(cmd)
                    # if r > 0:
                    #    logger.debug("TX: "+hex(startcmd[i]))
                    v = self.cdc.read(self.packetsizeread)
                    try:
                        self.cdc.setLineCoding(115200)
                        self.__logger.info("Setting 115200")
                    except:
                        pass
                    if len(v) < 1:
                        logger.debug("Timeout")
                        i = 0
                        time.sleep(0.005)
                    elif v[0] == res:
                        # logger.debug("RX OK: "+hex(startcmd[i])+"->"+hex(respcmd[i]))
                        i += 1
                    else:
                        self.cdc.setLineCoding(115200)
                        self.__logger.info("Setting 115200")
                        i = 0
                    tries -= 1
                print()
                self.__logger.info("Device detected :)")
                return True
            else:
                sys.stdout.write('.')
                if loop >= 20:
                    sys.stdout.write('\n')
                    loop = 0
                loop += 1
                time.sleep(0.3)
                sys.stdout.flush()
        return False

    def mtk_cmd(self, value, bytestoread=0, nocmd=False):
        resp = b""
        dlen = len(value)
        wr = self.usbwrite(value)
        if nocmd:
            cmdrsp = self.usbread(bytestoread)
            return cmdrsp
        else:
            cmdrsp = self.usbread(dlen)
            if cmdrsp[0] is not value[0]:
                print("Cmd error :" + hexlify(cmdrsp).decode('utf-8'))
                return -1
            if (bytestoread > 0):
                resp = self.usbread(bytestoread)
            return resp

    def da_get_blver(self):
        res = self.usbwrite(self.mtkcmd.CMD_GET_BL_VER.value)
        if res:
            res = self.usbread(1)
        return unpack("B", res)[0]

    def cmd_get_target_config(self):
        res = self.usbwrite(self.mtkcmd.CMD_GET_TARGET_CONFIG.value)
        if self.usbread(1) == self.mtkcmd.CMD_GET_TARGET_CONFIG.value:
            target_config, status = unpack(">IH", self.usbread(6))
            sbc = True if (target_config & 0x1) else False
            sla = True if (target_config & 0x2) else False
            daa = True if (target_config & 0x4) else False
            self.__logger.info(f"Target config: {hex(target_config)}")
            self.__logger.info(f"\tSBC enabled: {sbc}")
            self.__logger.info(f"\tSLA enabled: {sla}")
            self.__logger.info(f"\tDAA enabled: {daa}")

            if status > 0xff:
                raise ("Get Target Config Error")
            return {"sbc": sbc, "sla": sla, "daa": daa}
        else:
            self.__logger.warning("CMD Get_Target_Config not supported.")
            return {"sbc": False, "sla": False, "daa": False}

    def da_jump_da(self, addr):
        self.usbwrite(self.mtkcmd.CMD_JUMP_DA.value)
        cmd = self.usbread(1)
        if cmd == self.mtkcmd.CMD_JUMP_DA.value:
            self.usbwrite(pack(">I", addr))
            resaddr = unpack(">I", self.usbread(4))[0]
            if resaddr == addr:
                status = unpack(">H", self.usbread(2))[0]
                if status == 0:
                    return True
        return False

    def da_get_hwcode(self):
        res = self.mtk_cmd(self.mtkcmd.CMD_GET_HW_CODE.value, 4)  # 0xFD
        return unpack(">HH", res)

    def da_get_hw_sw_ver(self):
        res = self.mtk_cmd(self.mtkcmd.CMD_GET_HW_SW_VER.value, 8)  # 0xFC
        return unpack(">HHHH", res)

    def da_get_meid(self):
        res = self.mtk_cmd(self.mtkcmd.CMD_GET_ME_ID.value, 23, True)  # 0xE1
        return res

    def da_get_part_info(self):
        res = self.mtk_cmd(self.mtkdacmd.DA_SDMMC_READ_PMT_CMD.value, 1 + 4)  # 0xA5
        value, length = unpack(">BI", res)
        self.usbwrite(self.mtkcmd.ACK)
        data = self.usbread(length)
        self.usbwrite(self.mtkcmd.ACK)
        return data

    def da_check_security(self):
        cmd = self.mtkdacmd.DA_CHK_PC_SEC_INFO_CMD.value + pack(">I", 0)  # E0
        ack = self.mtk_cmd(cmd, 1)
        if ack == self.mtkcmd.ACK.value:
            return True
        return False

    def da_recheck(self):  # If Preloader is needed
        sec_info_len = 0
        cmd = self.mtkdacmd.DA_SECURE_USB_RECHECK_CMD.value + pack(">I", sec_info_len)  # B4
        status = struct.unpack(">I", self.mtk_cmd(cmd, 1))[0]
        if status == 0x1799:
            return False  # S-USBDL disabled
        return True

    def da_send(self, address, size, sig_len, dadata):
        cmd = self.mtkcmd.CMD_SEND_DA.value + pack(">III", address, size, sig_len)
        res = self.mtk_cmd(cmd, 2)  # 0xD4
        if res != -1:
            status = unpack(">H", res)[0]
            if status == 0:
                for pos in range(0, size, sig_len):
                    self.usbwrite(dadata[pos:pos + sig_len])
                wr = self.usbwrite(b"")
                res2 = self.usbread(4)
                checksum, status = unpack(">HH", res2)
                if status == 0x0:
                    return address
            else:
                return False
        return False

    def brom_send(self, dasetup, da, stage, packetsize=0x1000):
        offset = dasetup[stage]["m_buf"]
        size = dasetup[stage]["m_len"]
        address = dasetup[stage]["m_start_addr"]
        da.seek(offset)
        dadata = da.read(size)
        self.usbwrite(pack(">I", address))
        self.usbwrite(pack(">I", size))
        self.usbwrite(pack(">I", packetsize))
        buffer = self.usbread(1)
        for pos in range(0, size, packetsize):
            self.usbwrite(dadata[pos:pos + packetsize])
            buffer = self.usbread(1)
        time.sleep(0.5)
        self.usbwrite(self.mtkcmd.ACK.value)
        buffer = self.usbread(1)
        data = self.usbread(0xEC)
        flashinfo = read_object(data, bldrinfo)
        return flashinfo

    def da_read32(self, addr, dwords=1):
        result = []
        cmd = self.mtkcmd.CMD_READ32.value
        self.usbwrite(cmd)
        res = self.usbread(1)
        if res == cmd:
            self.usbwrite(pack(">I", addr))
            res2 = unpack(">I", self.usbread(4))[0]
            if res2 == addr:
                self.usbwrite(pack(">I", dwords))
                res3 = unpack(">I", self.usbread(4))[0]
                status = unpack(">H", self.usbread(2))[0]
                if res3 == dwords and status == 0:
                    data = self.usbread(4 * dwords)
                    for i in range(dwords):
                        resdword = unpack(">I", data[i * 4:(i * 4) + 4])[0]
                        result.append(resdword)
                    status2 = unpack(">H", self.usbread(2))[0]
                    if status2 == 0:
                        return result
        return result

    def da_write32(self, addr, dwords):
        cmd = self.mtkcmd.CMD_WRITE32.value
        self.usbwrite(cmd)
        res = self.usbread(1)
        if res == cmd:
            self.usbwrite(pack(">I", addr))
            res2 = unpack(">I", self.usbread(4))[0]
            if res2 == addr:
                self.usbwrite(pack(">I", len(dwords)))
                res3 = unpack(">I", self.usbread(4))[0]
                status = unpack(">H", self.usbread(2))[0]
                if res3 == len(dwords):
                    for dword in dwords:
                        self.usbwrite(pack(">I", dword))
                        resdword = unpack(">I", self.usbread(4))[0]
                        if resdword != dword:
                            break
                    status2 = unpack(">H", self.usbread(2))[0]
                    if status2 == 0:
                        return True
        return False

    def gcpu_init(self):
        self.da_write32(self.gcpu.GCPU_REG_MEM_P2, [0x0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P3, [0x0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P4, [0x0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P5, [0x0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P6, [0x0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P7, [0x0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P8, [0x0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P9, [0x0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P10, [0x0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_CMD + 18 * 4, [0, 0, 0, 0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_CMD + 22 * 4, [0, 0, 0, 0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_CMD + 26 * 4, [0, 0, 0, 0, 0, 0, 0, 0])

    def gcpu_acquire(self):
        self.da_write32(self.gcpu.cryptobase, [0x1F, 0x12000])

    def gcpu_call_func(self, func):
        self.da_write32(self.gcpu.GCPU_REG_INT_CLR, [3])
        self.da_write32(self.gcpu.GCPU_REG_INT_EN, [3])
        self.da_write32(self.gcpu.GCPU_REG_MEM_CMD, [func])
        self.da_write32(self.gcpu.GCPU_REG_PC_CTL, [0])
        while not self.da_read32(self.gcpu.GCPU_REG_INT_SET)[0]:
            pass
        if self.da_read32(self.gcpu.GCPU_REG_INT_SET)[0] & 2:
            if not self.da_read32(self.gcpu.GCPU_REG_INT_SET)[0] & 1:
                while not self.da_read32(self.gcpu.GCPU_REG_INT_SET)[0]:
                    pass
            result = -1
            self.da_write32(self.gcpu.GCPU_REG_INT_CLR, [3])
        else:
            while not self.da_read32(self.gcpu.cryptobase + 0x418)[0] & 1:
                pass
            result = 0
            self.da_write32(self.gcpu.GCPU_REG_INT_CLR, [3])
        return result

    def aes_read16(self, addr):
        self.da_write32(self.gcpu.GCPU_REG_MEM_P0, [addr])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P1, [0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P2, [1])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P4, [18])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P5, [26])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P6, [26])
        if self.gcpu_call_func(126) != 0:  # aes decrypt
            raise Exception("failed to call the function!")
        res = self.da_read32(self.gcpu.GCPU_REG_MEM_CMD + 26 * 4, 4)  # read out of the IV
        data = b""
        for word in res:
            data += pack("<I", word)
        return data

    def aes_write16(self, addr, data):
        if len(data) != 16:
            raise RuntimeError("data must be 16 bytes")

        pattern = bytes.fromhex("4dd12bdf0ec7d26c482490b3482a1b1f")

        # iv-xor
        words = []
        for x in range(4):
            word = data[x * 4:(x + 1) * 4]
            word = unpack("<I", word)[0]
            pat = unpack("<I", pattern[x * 4:(x + 1) * 4])[0]
            words.append(word ^ pat)

        self.da_write32(self.gcpu.GCPU_REG_MEM_CMD + 18 * 4, [0, 0, 0, 0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_CMD + 22 * 4, [0, 0, 0, 0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_CMD + 26 * 4, [0, 0, 0, 0, 0, 0, 0, 0])

        self.da_write32(self.gcpu.GCPU_REG_MEM_CMD + 26 * 4, [words])

        # src to VALID address which has all zeroes (otherwise, update pattern)
        self.da_write32(self.gcpu.GCPU_REG_MEM_P0, [0])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P1, [addr])  # dst to our destination
        self.da_write32(self.gcpu.GCPU_REG_MEM_P2, [1])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P4, [18])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P5, [26])
        self.da_write32(self.gcpu.GCPU_REG_MEM_P6, [26])
        if self.gcpu_call_func(126) != 0:  # aes decrypt
            raise RuntimeError("failed to call the function!")

    def run_ext_cmd(self, cmd):
        self.usbwrite(b'\xC8')
        assert self.usbread(1) == b'\xC8'
        cmd = bytes([cmd])
        self.usbwrite(cmd)
        assert self.usbread(1) == cmd
        self.usbread(1)
        self.usbread(2)

    def echo(self, data):
        if isinstance(data, bytes):
            data = [data]
        for val in data:
            self.usbwrite(val)
            tmp = self.usbread(len(val))
            if val != tmp:
                return False
        return True

    def fix_payload(self,payloadfilename, da=True):
        with open(payloadfilename, "rb") as rf:
            payload = bytearray(rf.read())
            wd=unpack("<I", payload[-4:])[0]
            ua=unpack("<I", payload[-8:-4])[0]
            if wd == 0x10007000:
                payload[-4:] = pack("<I", self.watchdog_addr)
            if ua == 0x11002000:
                payload[-8:-4] = pack("<I", self.uart_addr)
            while len(payload) % 4 != 0:
                payload.append(0)
            if da:
                payload.extend(b"\x00"*0x100) #signature len
            return payload

    def revdword(self,value):
        return unpack(">I",pack("<I",value))[0]

    def kamakiri(self, payload):
        addr = self.watchdog_addr + 0x50
        self.da_write32(addr, [self.revdword(self.brom_address)])
        if self.var_0:
            self.da_read32(addr - self.var_0, (self.var_0 + 4) // 4)
        else:
            for i in range(0, 15):
                self.da_read32(addr - (15 - i) * 4, 15 - i + 1)
        if len(payload) >= 0xA00:
            raise ("Kamakiri Payload is too large")
        self.echo(b"\xE0")
        self.echo(pack(">I", len(payload)))
        self.usbread(2)
        self.usbwrite(payload)
        self.usbread(4)
        try:
            # noinspection PyProtectedMember
            #self.cdc.device._ctx.managed_claim_interface = lambda *args, **kwargs: None
            self.cdc.device.ctrl_transfer(0xA1, 0, 0, self.var_1, 0)
        except usb.core.USBError as e:
            print(e)
        return True

    #def amonet(self,payload):

    def payload(self,payloadfilename):
        if self.target_config["sla"] or self.target_config["daa"]:
            payload = self.fix_payload(payloadfilename, False)
            self.__logger.info("Trying kamakiri..")
            if self.kamakiri(payload):
                self.__logger.info("Done sending payload...")
                return True
        else:
            self.__loader.info("Sending payload via insecure da.")
            payload = self.fix_payload(payloadfilename)
            if self.da_send(self.payload_address, len(payload) - 0x100, 0x100, payload):
                if self.da_jump_da(self.payload_address):
                    self.__logger.info("Done sending payload...")
                    return True
        self.__logger.error("Error on sending payload.")
        return False


    def dump_brom(self, filename, type):
        if type == "amonet":
            self.__logger.info("Amonet Init Crypto Engine")
            self.gcpu_init()
            self.gcpu_acquire()
            self.gcpu_init()
            self.gcpu_acquire()
            self.__logger.info("Amonet Disable Caches")
            self.run_ext_cmd(0xB1)
            #self.__logger.info("Disable bootrom range checks")
            #self.aes_write16(0x102868, bytes.fromhex("00000000000000000000000080000000"))

            self.__logger.info("Amonet Run")
            print_progress(0, 100, prefix='Progress:', suffix='Complete', bar_length=50)
            old = 0
            with open(filename, 'wb') as wf:
                for addr in range(0x0, 0x20000, 16):
                    prog = int(addr / 0x20000 * 100)
                    if int(prog) > old:
                        print_progress(prog, 100, prefix='Progress:', suffix='Complete, addr %08X' % addr,
                                       bar_length=50)
                        old = prog
                    wf.write(self.aes_read16(addr))
            print_progress(100, 100, prefix='Progress:', suffix='Complete', bar_length=50)
            self.__logger.info("Bootrom dumped as: " + filename)
        elif type=="kamakiri":
            self.__logger.info("Kamakiri / DA Run")
            if self.payload(os.path.join("payloads","generic_dump_payload.bin")):
                result = self.usbread(4)
                if result == pack(">I", 0xC1C2C3C4):
                    old=0
                    with open(filename, 'wb') as wf:
                        print_progress(0, 100, prefix='Progress:', suffix='Complete', bar_length=50)
                        for addr in range(0x0, 0x20000, 16):
                            prog = int(addr / 0x20000 * 100)
                            if int(prog) > old:
                                print_progress(prog, 100, prefix='Progress:', suffix='Complete, addr %08X' % addr,
                                               bar_length=50)
                                old = prog
                        print_progress(100, 100, prefix='Progress:', suffix='Complete', bar_length=50)
                        self.__logger.info("Bootrom dumped as: "+filename)
                    return True
                elif result==pack(">I", 0x0000C1C2):
                    self.__logger.info("Word mode detected.")
                    result=self.usbread(4)
                    if result==pack(">I", 0xC1C2C3C4):
                        with open(filename, "wb") as wf:
                            for i in range(0x20000 // 4):
                                data=self.usbread(8)
                                wf.write(data[4:])
                        self.__logger.info("Bootrom dumped as: " + filename)
                        return True
                self.__logger.error("Error: "+hexlify(result))

    def get_watchdog_addr(self, hwcode):
        if self.watchdog_addr==0:
            if hwcode in [0x6276, 0x8163]:  # A1
                self.watchdog_addr=0x2200
                return 0x2200, 0x610C0000
            elif hwcode in [0x6251, 0x6516]:
                self.watchdog_addr=0x2200
                return 0x2200, 0x80030000
            elif hwcode in [0x6255, 0x6516]:
                self.watchdog_addr=0x2200
                return 0x2200, 0x701E0000
            elif hwcode in [0x6571]:  # 8B
                self.watchdog_addr=0x10007400
                return 0x10007400, 0x22000000
            elif hwcode in [0x6572, 0x2601, 0x6592, 0x6595, 0x6755, 0x6757, 0x6797, 0x6798, 0x6799, 0x0571, 0x0598,
                            0x326]:  # 88,90,8A,8C,B4,BA BB=6757D,B5,BC BF,B6,B7,B9=ELBRUS
                self.watchdog_addr=0x10007000
                return 0x10007000, 0x22000000
            elif hwcode in [0x6573]:  # 83
                self.watchdog_addr=0x2200
                return 0x2200, 0x70025000
            elif hwcode in [0x6575, 0x6577]:  # 84,85
                self.watchdog_addr=0xC0000000
                return 0xC0000000,0x0
            elif hwcode in [0x6570, 0x8167, 0x6580, 0x699]:  # BE,BD,9C
                self.watchdog_addr=0x10007000
                return 0x10007000, 0x22000064
            elif hwcode in [0x6583, 0x6589, 0x8135]:  # ,86,9C,89
                self.watchdog_addr = 0x10000000
                return 0x10000000, 0x22002224
            elif hwcode in [0x6735, 0x6753, 0x6737, 0x335]:  # 9B=6735M 9D,9E,9F=6737T A0=6737M
                self.watchdog_addr = 0x10212000
                return 0x10212000, 0x22000000
            else:
                self.watchdog_addr = 0x10007000
                return 0x10007000, 0x22000064
        '''
            case 0x6582: //0x87
            case 0x8127: //0x8D
            case 0x8173: //0x8E
            case 0x6752: //0x8F
            case 0x6795: //0x9A
            case 0x8590: //0x91
            case 0x7623: //0x92
            case 0x7683: //0x93
            case 0x8521: //0x99
        '''

    def SetReg_DisableWatchDogTimer(self, hwcode):
        '''
        SetReg_DisableWatchDogTimer; BRom_WriteCmd32(): Reg 0x10007000[1]={ Value 0x22000000 }.
        '''
        addr, value = self.get_watchdog_addr(hwcode)
        res = self.da_write32(addr, [value])
        if not res:
            self.__logger.error("Received wrong SetReg_DisableWatchDogTimer response")
            return False
        if hwcode == 0x6592:
            res = self.da_write32(0x10000500, [0x22000000])
            if res:
                return True
        elif hwcode in [0x6575, 0x6577]:
            res = self.da_write32(0x2200, [0xC0000000])
            if res:
                return True
        else:
            return True
        return False

    def bmtsettings(self, hwcode):
        bmtflag = 1
        bmtblockcount = 0
        bmtpartsize = 0
        if hwcode in [0x6592, 0x6582, 0x8127, 0x6571]:
            if self.flash == "emmc":
                bmtflag = 1
                bmtblockcount = 0xA8
                bmtpartsize = 0x1500000
        elif hwcode in [0x6570, 0x8167, 0x6580, 0x6735, 0x6753, 0x6755, 0x6752, 0x6595, 0x6795, 0x6797, 0x8163]:
            bmtflag = 1
            bmtpartsize = 0
        elif hwcode in [0x6571]:
            if self.flash == "nand":
                bmtflag = 0
                bmtblockcount = 0x38
                bmtpartsize = 0xe00000
            elif self.flash == "emmc":
                bmtflag = 1
                bmtblockcount = 0xA8
                bmtpartsize = 0x1500000
        elif hwcode in [0x6575]:
            if self.flash == "nand":
                bmtflag = 0
                bmtblockcount = 0x50
            elif self.flash == "emmc":
                bmtflag = 1
                bmtblockcount = 0xA8
                bmtpartsize = 0x1500000
        elif hwcode in [0x6572]:
            if self.flash == "nand":
                bmtflag = 0
                bmtpartsize = 0xA00000
                bmtblockcount = 0x50
            elif self.flash == "emmc":
                bmtflag = 1
                bmtblockcount = 0xA8
                bmtpartsize = 0x0
        elif hwcode in [0x6577, 0x6583, 0x6589]:
            if self.flash == "nand":
                bmtflag = 0
                bmtpartsize = 0xA00000
                bmtblockcount = 0xA8
        return bmtflag, bmtblockcount, bmtpartsize

    def set_stage2_config(self, hwcode):
        # m_nor_chip_select[0]="CS_0"(0x00), m_nor_chip_select[1]="CS_WITH_DECODER"(0x08)
        m_nor_chip = 0x08
        self.usbwrite(pack(">H", m_nor_chip))
        m_nor_chip_select = 0x00
        self.usbwrite(pack("B", m_nor_chip_select))
        m_nand_acccon = 0x7007FFFF
        self.usbwrite(pack(">I", m_nand_acccon))
        bmtflag, bmtblockcount, bmtpartsize = self.bmtsettings(hwcode)
        self.usbwrite(pack("B", bmtflag))
        self.usbwrite(pack(">I", bmtpartsize))
        # self.usbwrite(pack(">I", bmtblockcount))
        # unsigned char force_charge=0x02; //Setting in tool: 0x02=Auto, 0x01=On
        force_charge = 0x02
        self.usbwrite(pack("B", force_charge))
        resetkeys = 0x01  # default
        if hwcode == 0x6583:
            resetkeys = 0
        self.usbwrite(pack("B", resetkeys))
        # EXT_CLOCK: ext_clock(0x02)="EXT_26M".
        extclock = 0x02
        self.usbwrite(pack("B", extclock))
        msdc_boot_ch = 0
        self.usbwrite(pack("B", msdc_boot_ch))
        toread = 4
        if hwcode == 0x6592:
            is_gpt_solution = 0
            self.usbwrite(pack(">I", is_gpt_solution))
            toread = (6 * 4)
        elif hwcode == 0x8163:
            SLC_percent = 0x20000
            self.usbwrite(pack(">I", SLC_percent))
        elif hwcode == 0x6580:
            SLC_percent = 0x1
            self.usbwrite(pack(">I", SLC_percent))
            unk = b"\x46\x46\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\x00\x00\x00"
            self.usbwrite(unk)
        elif hwcode in [0x6583, 0x6589]:
            if hwcode == 0x6583:
                forcedram = 0
            elif hwcode == 0x6589:
                forcedram = 1
            self.usbwrite(pack(">I", forcedram))
        elif hwcode == 0x8127:
            skipdl = 0
            self.usbwrite(pack(">I", skipdl))
        elif hwcode == 0x6582:
            newcombo = 0
            self.usbwrite(pack(">I", newcombo))
        time.sleep(0.350)
        buffer = self.usbread(toread)
        return buffer

    def da_upload(self, hwcode, blver, daconfig):
        if blver == 0x01:
            self.__logger.info("Uploading stage 1...")
            with open(self.loader, 'rb') as bootldr:
                # stage 1
                stage = blver + 1
                offset = self.da_setup[stage]["m_buf"]
                size = self.da_setup[stage]["m_len"]
                address = self.da_setup[stage]["m_start_addr"]
                sig_len = self.da_setup[stage]["m_sig_len"]
                bootldr.seek(offset)
                dadata = bootldr.read(size)
                addr = self.da_send(address, size, sig_len, dadata)
                if addr != False:
                    if self.da_jump_da(addr):
                        sync = self.usbread(1)
                        if sync != b"\xC0":
                            self.__logger.error("Error on DA sync")
                            return
                nandinfo = unpack(">I", self.usbread(4))[0]
                ids = unpack(">H", self.usbread(2))[0]
                nandids = []
                for i in range(0, ids):
                    tmp = unpack(">H", self.usbread(2))[0]
                    nandids.append(tmp)

                emmcinfo = unpack(">I", self.usbread(4))[0]
                emmcids = []
                for i in range(0, 4):
                    tmp = unpack(">I", self.usbread(4))[0]
                    emmcids.append(tmp)

                if nandids[0] != 0:
                    self.flash = "nand"
                elif emmcids[0] != 0:
                    self.flash = "emmc"
                else:
                    self.flash = "nor"

                self.usbwrite(self.mtkcmd.ACK.value)
                ackval = self.usbread(3)

                self.usbwrite(self.mtkcmd.CMD_GET_VERSION.value)
                self.usbwrite(pack("B", blver))

                buffer = self.set_stage2_config(hwcode)
                self.__logger.info("Uploading stage 2...")
                # stage 2
                flashinfo = self.brom_send(daconfig, bootldr, blver + 2)
                if self.flash == "nand":
                    self.flashsize = flashinfo["m_nand_flash_size"]
                elif self.flash == "emmc":
                    self.flashsize = flashinfo["m_emmc_ua_size"]
                    if self.flashsize == 0:
                        self.flashsize = flashinfo["m_sdmmc_ua_size"]
                elif self.flash == "nor":
                    self.flashsize = flashinfo["m_nor_flash_size"]
                return flashinfo

    def initmtk(self):
        self.__logger.info("Status: Waiting for PreLoader VCOM, please connect mobile")
        if not self.detect():
            self.__logger.error("No MTK PreLoader detected.")
            exit(0)

        res = self.usbwrite(self.mtkcmd.CMD_GET_HW_CODE.value)  # 0xFD
        respcmd = unpack("B", self.usbread(1))[0]
        cmd = self.mtkcmd.CMD_GET_HW_CODE.value
        if respcmd != cmd[0]:
            self.__logger.error("Sync error. Please power off the device and retry.")
            exit(0)
        else:
            self.hwcode = unpack(">H", self.usbread(2))[0]
            self.hwver = unpack(">H", self.usbread(2))[0]
        self.gcpu = GCPU(self.hwcode)
        self.__logger.info("HW code:\t\t" + hex(self.hwcode))
        if self.hwcode in hwcodetable:
            self.__logger.info("CPU:\t\t\t" + hwcodetable[self.hwcode])
        else:
            self.__logger.info("CPU:\t\t\tUnknown")
        self.__logger.info("HW version:\t" + hex(self.hwver))
        res = self.da_get_hw_sw_ver()
        self.hwsubcode = 0
        self.hwver = 0
        self.swver = 0
        if res != -1:
            self.hwsubcode = res[0]
            self.hwver = res[1]
            self.swver = res[2]
        self.__logger.info("HW subcode:\t" + hex(self.hwsubcode))
        self.__logger.info("HW Ver:\t\t" + hex(self.hwver))
        self.__logger.info("SW Ver:\t\t" + hex(self.swver))
        self.target_config = self.cmd_get_target_config()

        self.__logger.info("Disabling Watchdog...")
        self.SetReg_DisableWatchDogTimer(self.hwcode)  # D4

        self.daconfig = None
        for setup in self.da_setup:
            if setup[0]["hw_code"] == self.hwcode:
                if setup[0]["hw_version"] == self.hwver:
                    if setup[0]["sw_version"] == self.swver:
                        self.daconfig = setup
                        break
        if self.daconfig == None:
            self.__logger.error("No da config set up")

        '''
        #meid=self.da_get_meid()
        res=self.da_read32(0x10008008,1)
        for item in res:
            print(hex(item))
        res=self.da_write32(0x10200004, [2,2,0x110])
        res=self.da_write32(0x10200040, [0x9ED40400,0xE884A1,0xE3F083BD,0x2F4E6D8A])
        res=self.da_write32(0x10200010, [0,0,0,0])
        res=self.da_write32(0x10200008, [1])
        res=self.da_read32(0x100100,1)
        print("HWUID: ")
        for item in res:
            print(hexlify(item.to_bytes(4, byteorder='big')))

        res=self.da_read32(0x10009040,1) #D1
        if res != -1:
            if res[0]==0x1002: #6580
                res=res
        '''

    def upload_da(self):
        self.blver = self.da_get_blver()
        self.__logger.info("Uploading da...")
        flashinfo = self.da_upload(self.hwcode, self.blver + 1, self.daconfig)
        if flashinfo == -1:
            exit(1)
        else:
            if flashinfo["ack"] == 0x5a:
                self.flashinfo = flashinfo
                for info in flashinfo:
                    value = flashinfo[info]
                    if info == "ack":
                        break
                    subtype = type(value)
                    if subtype is bytes:
                        self.__logger.info(info + ": " + hexlify(value).decode('utf-8'))
                    elif subtype is int:
                        self.__logger.info(info + ": " + hex(value))

    def da_check_usb_cmd(self):
        if self.usbwrite(self.mtkdacmd.DA_USB_CHECK_STATUS.value):  # 72
            res = self.usbread(2)
            if len(res) > 1:
                if res[0] is self.mtkdacmd.ACK.value:
                    return True
        return False

    def sdmmc_switch_part(self):
        self.usbwrite(self.mtkdacmd.DA_SDMMC_SWITCH_PART_CMD.value)  # 60
        ack = self.usbread(1)
        if ack == self.mtkcmd.ACK.value:
            partition = 0x8  # EMMC_Part_User = 0x8, sonst 0x0
            self.usbwrite(pack("B", partition))
            ack = self.usbread(1)
            if ack == self.mtkcmd.ACK.value[0]:
                return True
        return False

    def da_finish(self, value):
        self.usbwrite(self.mtkdacmd.DA_FINISH_CMD.value)  # D9
        ack = self.usbread(1)[0]
        if ack is self.mtkcmd.ACK.value:
            self.usbwrite(pack(">I", value))
            ack = self.usbread(1)[0]
            if ack is self.mtkcmd.ACK.value[0]:
                return True
        return False

    def writeflash(self, addr, length, filename, display=True):
        return True

    def readflash(self, addr, length, filename, display=True):
        self.da_check_usb_cmd()
        packetsize = 0x0
        if self.flash == "emmc":
            self.sdmmc_switch_part()
            packetsize = 0x100000
            self.usbwrite(self.mtkdacmd.DA_READ_CMD.value)  # D6
            self.usbwrite(b"\x0C")  # Host:Linux, 0x0B=Windows
            self.usbwrite(b"\x02")  # Storage-Type: EMMC
            self.usbwrite(pack(">Q", addr))
            self.usbwrite(pack(">Q", length))
            self.usbwrite(pack(">I", packetsize))
            ack = self.usbread(1)[0]
            if ack is not self.mtkdacmd.ACK.value[0]:
                self.__logger.error("Error on sending read command")
                exit(1)
            self.readsize = self.flashsize
        elif self.flash == "nand":
            self.usbwrite(self.mtkdacmd.DA_NAND_READPAGE.value)  # DF
            self.usbwrite(b"\x0C")  # Host:Linux, 0x0B=Windows
            self.usbwrite(b"\x00")  # Storage-Type: NUTL_READ_PAGE_SPARE
            self.usbwrite(b"\x01")  # Addr-Type: NUTL_ADDR_LOGICAL
            self.usbwrite(pack(">I", addr))
            self.usbwrite(pack(">I", length))
            self.usbwrite(pack(">I", 0))
            ack = self.usbread(1)[0]
            if ack is not self.mtkdacmd.ACK.value[0]:
                self.__logger.error("Error on sending read command")
                exit(1)
            self.pagesize = unpack(">I", self.usbread(4))[0]
            self.sparesize = unpack(">I", self.usbread(4))[0]
            packetsize = unpack(">I", self.usbread(4))[0]
            pagestoread = 1
            self.usbwrite(pack(">I", pagestoread))
            buffer = unpack(">I", self.usbread(4))[0]
            self.readsize = self.flashsize // self.pagesize * (self.pagesize + self.sparesize)
        if display:
            print_progress(0, 100, prefix='Progress:', suffix='Complete', bar_length=50)
        old = 0

        if filename != "":
            with open(filename, "wb") as wf:
                bytestoread = length
                while (bytestoread > 0):
                    size = bytestoread
                    if bytestoread > packetsize:
                        size = packetsize
                    for i in range(0, size, 0x400):
                        data = self.usbread(0x400)
                        bytestoread -= len(data)
                        wf.write(data)
                    checksum = unpack(">H", self.usbread(2))[0]
                    self.usbwrite(self.mtkdacmd.ACK.value)
                    if display:
                        prog = (length - bytestoread) / length * 100
                        if int(prog) > old:
                            print_progress(prog, 100, prefix='Progress:', suffix='Complete', bar_length=50)
                            old = prog
                return True
        else:
            buffer = b""
            bytestoread = length
            while (bytestoread > 0):
                size = bytestoread
                if bytestoread > packetsize:
                    size = packetsize
                for i in range(0, size, 0x400):
                    data = self.usbread(0x400)
                    bytestoread -= len(data)
                    buffer += data
                checksum = unpack(">H", self.usbread(2))[0]
                self.usbwrite(self.mtkdacmd.ACK.value)
                if display:
                    prog = (length - bytestoread) / length * 100
                    if int(prog) > old:
                        print_progress(prog, 100, prefix='Progress:', suffix='Complete', bar_length=50)
                        old = prog
            return buffer


class Main(metaclass=LogBase):
    def detect_partition(self, mtk, arguments, partitionname):
        fpartitions = []
        data, guid_gpt = mtk.get_gpt(int(arguments["--gpt-num-part-entries"]),
                                     int(arguments["--gpt-part-entry-size"]),
                                     int(arguments["--gpt-part-entry-start-lba"]))
        if guid_gpt is None:
            return [False, fpartitions]
        else:
            for partition in guid_gpt.partentries:
                fpartitions.append(partition)
                if partition.name == partitionname:
                    return [True, partition]
        return [False, fpartitions]

    def detectusbdevices(self):
        dev = usb.core.find(find_all=True)
        ids = [deviceclass(cfg.idVendor, cfg.idProduct) for cfg in dev]
        return ids

    def run(self):
        vid = int(args["--vid"], 16)
        pid = int(args["--pid"], 16)
        if args["--debugmode"]:
            logfilename = "log.txt"
            if os.path.exists(logfilename):
                os.remove(logfilename)
            fh = logging.FileHandler(logfilename)
            self.__logger.addHandler(fh)
            self.__logger.setLevel(logging.DEBUG)
        else:
            self.__logger.setLevel(logging.INFO)
        interface = -1
        pagesize = int(args["--sectorsize"], 16)

        if args["dumpbrom"]:
            if vid != 0xE8D and pid != 0x0003:
                mtk = Mtk(loader=args["--loader"], loglevel=self.__logger.level, vid=vid, pid=pid, interface=interface,
                          pagesize=pagesize, args=args)
                mtk.initmtk()
                self.__logger.info("Crashing da... (entering bootrom)")
                mtk.da_send(0, 0x100, 0x100, b'\x00' * 0x100)
            preloader = Mtk(loader=args["--loader"], loglevel=self.__logger.level, vid=0xE8D, pid=0x0003, interface=1,
                            pagesize=pagesize, args=args)
            preloader.initmtk()
            filename=args["--filename"]
            if filename==None:
                if mtk.hwcode in hwcodetable:
                    cpu="_"+hwcodetable[mtk.hwcode]
                else:
                    cpu=""
                filename="brom"+cpu+"_"+hex(mtk.hwcode)[2:]+".bin"
            if args["--ptype"]=="amonet":
                preloader.dump_brom(filename, "amonet")
            elif args["--ptype"]=="kamakiri":
                preloader.dump_brom(filename, "kamakiri")
            else:
                preloader.dump_brom(filename, "kamakiri")
            sys.exit(0)
        elif args["crash"]:
            mtk = Mtk(loader=args["--loader"], loglevel=self.__logger.level, vid=vid, pid=pid, interface=interface,
                      pagesize=pagesize, args=args)
            mtk.initmtk()
            self.__logger.info("Crashing da...")
            mtk.da_send(0, 0x100, 0x100, b'\x00' * 0x100)
            sys.exit(0)
        elif args["payload"]:
            mtk = Mtk(loader=args["--loader"], loglevel=self.__logger.level, vid=vid, pid=pid, interface=interface,
                      pagesize=pagesize, args=args)
            mtk.initmtk()
            payloadfile = args["--payload"]
            if payloadfile == "":
                payloadfile = "payloads/generic_dump_payload.bin"
                if mtk.payload(payloadfile):
                    result = self.usbread(4)
                    if result == pack("<I", 0xA1A2A4A4):
                        self.__logger.info("Payload succeeded")
                    else:
                        self.__logger.warning("Result: " + hexlify(result))
            sys.exit(0)
        elif args["gettargetconfig"]:
            mtk = Mtk(loader=args["--loader"], loglevel=self.__logger.level, vid=vid, pid=pid, interface=interface,
                      pagesize=pagesize,args=args)
            mtk.initmtk()
            self.__logger.info("Getting target info...")
            mtk.cmd_get_target_config()
            sys.exit(0)
        else:
            mtk = Mtk(loader=args["--loader"], loglevel=self.__logger.level, vid=vid, pid=pid, interface=interface,
                      pagesize=pagesize,args=args)
            mtk.initmtk()
            mtk.upload_da()

        if args["gpt"]:
            directory = args["<directory>"]
            if directory is None:
                directory = ""

            sfilename = os.path.join(directory, f"gpt_main.bin")
            data, guid_gpt = mtk.get_gpt(int(args["--gpt-num-part-entries"]),
                                         int(args["--gpt-part-entry-size"]),
                                         int(args["--gpt-part-entry-start-lba"]))
            if guid_gpt is None:
                self.__logger.error("Error reading gpt")
                mtk.da_finish(0x0)
                exit(1)
            else:
                with open(sfilename, "wb") as wf:
                    wf.write(data)

                print(f"Dumped GPT from to {sfilename}")
                sfilename = os.path.join(directory, f"gpt_backup.bin")
                with open(sfilename, "wb") as wf:
                    wf.write(data[mtk.pagesize:])
                print(f"Dumped Backup GPT to {sfilename}")
            mtk.da_finish(0x0)  # DISCONNECT_USB_AND_RELEASE_POWERKEY
            exit(0)
        elif args["printgpt"]:
            data, guid_gpt = mtk.get_gpt(int(args["--gpt-num-part-entries"]), int(args["--gpt-part-entry-size"]),
                                         int(args["--gpt-part-entry-start-lba"]))
            if guid_gpt is None:
                self.__logger.error("Error reading gpt")
                mtk.da_finish(0x0)
                exit(1)
            else:
                guid_gpt.print()
            mtk.da_finish(0x0)  # DISCONNECT_USB_AND_RELEASE_POWERKEY
            exit(0)
        elif args["r"]:
            partitionname = args["<partitionname>"]
            filename = args["<filename>"]
            filenames = filename.split(",")
            partitions = partitionname.split(",")
            if len(partitions) != len(filenames):
                self.__logger.error("You need to gives as many filenames as given partitions.")
                mtk.da_finish(0x0)  # DISCONNECT_USB_AND_RELEASE_POWERKEY
                exit(0)
            i = 0
            for partition in partitions:
                partfilename = filenames[i]
                i += 1
                res = detect_partition(mtk, args, partition)
                if res[0] == True:
                    rpartition = res[1]
                    mtk.readflash(rpartition.sector * mtk.pagesize, rpartition.sectors * mtk.pagesize, partfilename)
                    print(
                        f"Dumped sector {str(rpartition.sector)} with sector count {str(rpartition.sectors)} as {partfilename}.")
                else:
                    self.__logger.error(f"Error: Couldn't detect partition: {partition}\nAvailable partitions:")
                    for rpartition in res[1]:
                        self.__logger.error(rpartition)
            mtk.da_finish(0x0)  # DISCONNECT_USB_AND_RELEASE_POWERKEY
            exit(0)
        elif args["rl"]:
            directory = args["<directory>"]
            if args["--skip"]:
                skip = args["--skip"].split(",")
            else:
                skip = []
            if not os.path.exists(directory):
                os.mkdir(directory)
            data, guid_gpt = mtk.get_gpt(int(args["--gpt-num-part-entries"]),
                                         int(args["--gpt-part-entry-size"]),
                                         int(args["--gpt-part-entry-start-lba"]))
            if guid_gpt is None:
                self.__logger.error("Error reading gpt")
                mtk.da_finish(0x0)
                exit(1)
            else:
                storedir = directory
                if not os.path.exists(storedir):
                    os.mkdir(storedir)
                sfilename = os.path.join(storedir, f"gpt_main.bin")
                with open(sfilename, "wb") as wf:
                    wf.write(data)

                sfilename = os.path.join(storedir, f"gpt_backup.bin")
                with open(sfilename, "wb") as wf:
                    wf.write(data[mtk.pagesize * 2:])

                for partition in guid_gpt.partentries:
                    partitionname = partition.name
                    if partition.name in skip:
                        continue
                    filename = os.path.join(storedir, partitionname + ".bin")
                    logging.info(
                        f"Dumping partition {str(partition.name)} with sector count {str(partition.sectors)} as {filename}.")
                    mtk.readflash(partition.sector * mtk.pagesize, partition.sectors * mtk.pagesize, filename)
            mtk.da_finish(0x0)  # DISCONNECT_USB_AND_RELEASE_POWERKEY
            exit(0)
        elif args["rf"]:
            filename = args["<filename>"]
            data, guid_gpt = mtk.get_gpt(int(args["--gpt-num-part-entries"]), int(args["--gpt-part-entry-size"]),
                                         int(args["--gpt-part-entry-start-lba"]))
            if guid_gpt is None:
                self.__logger.error("Error reading gpt")
                mtk.da_finish(0x0)
                exit(1)
            else:
                sfilename = filename
                print(f"Dumping sector 0 with flash size {hex(mtk.flashsize)} as {filename}.")
                mtk.readflash(0, mtk.flashsize, sfilename)
                print(f"Dumped sector 0 with flash size {hex(mtk.flashsize)} as {filename}.")
            mtk.da_finish(0x0)  # DISCONNECT_USB_AND_RELEASE_POWERKEY
            exit(0)
        elif args["rs"]:
            start = int(args["<start_sector>"])
            sectors = int(args["<sectors>"])
            filename = args["<filename>"]
            mtk.readflash(0, start * mtk.pagesize, sectors * mtk.pagesize, filename)
            print(f"Dumped sector {str(start)} with sector count {str(sectors)} as {filename}.")
            mtk.da_finish(0x0)  # DISCONNECT_USB_AND_RELEASE_POWERKEY
            exit(0)
        elif args["footer"]:
            filename = args["<filename>"]
            data, guid_gpt = mtk.get_gpt(int(args["--gpt-num-part-entries"]), int(args["--gpt-part-entry-size"]),
                                         int(args["--gpt-part-entry-start-lba"]))
            if guid_gpt is None:
                self.__logger.error("Error reading gpt")
                mtk.da_finish(0x0)
                exit(1)
            else:
                pnames = ["userdata2", "metadata", "userdata", "reserved1", "reserved2", "reserved3"]
                for partition in guid_gpt.partentries:
                    if partition.name in pnames:
                        print(f"Detected partition: {partition.name}")
                        if partition.name in ["userdata2", "userdata"]:
                            data = mtk.readflash((partition.sector + partition.sectors) * mtk.pagesize - 0x4000, 0x4000,
                                                 "", False)
                        else:
                            data = mtk.readflash(partition.sector * mtk.pagesize, 0x4000, "", False)
                        if data == b"":
                            continue
                        val = struct.unpack("<I", data[:4])[0]
                        if (val & 0xFFFFFFF0) == 0xD0B5B1C0:
                            with open(filename, "wb") as wf:
                                wf.write(data)
                                print(f"Dumped footer from {partition.name} as {filename}.")
                                mtk.da_finish(0x0)
                                exit(0)
            self.__logger.error(f"Error: Couldn't detect footer partition.")
        elif args["reset"]:
            mtk.da_finish(0x0)
            exit(0)


if __name__ == '__main__':
    print("MTK Flash Client V1.0 (c) B.Kerler 2020-2021")
    mtk = Main().run()

'''
#!/usr/bin/env python3

import argparse
import binascii
import serial
import struct
import sys
import time


def auto_int(i):
    return int(i, 0)

def hex_int(i):
    return int(i, 16)


class ChecksumError(Exception):
    pass

class EchoBytesMismatchException(Exception):
    pass

class NotEnoughDataException(Exception):
    pass

class ProtocolError(Exception):
    pass

class UsbDl:
    commands = {
        'CMD_C8': 0xC8, # Don't know the meaning of this yet.
        'CMD_READ32': 0xD1,
        'CMD_WRITE32': 0xD4,
        'CMD_JUMP_DA': 0xD5,
        'CMD_JUMP_BL': 0xD6,
        'CMD_SEND_DA': 0xD7,
        'CMD_GET_TARGET_CONFIG': 0xD8,
        'CMD_UART1_LOG_EN': 0xDB,
        'CMD_UART1_SET_BAUD': 0xDC, # Not sure what the real name of this command is.
        'CMD_GET_BROM_LOG': 0xDD, # Not sure what the real name of this command is.
        'SCMD_GET_ME_ID': 0xE1,
        'CMD_GET_HW_SW_VER': 0xFC,
        'CMD_GET_HW_CODE': 0xFD,
    }

    socs = {
        0x0279: {
            'name': "MT6797",
            'brom': (0x00000000, 0x14000),
            'sram': (0x00100000, 0x30000),
            'l2_sram': (0x00200000, 0x100000), # Functional spec says address is 0x00400000, but that's incorrect.
            'toprgu': (0x10007000, 0x1000),
            'efusec': (0x10206000, 0x1000),
            'usbdl': 0x10001680,
            'cqdma_base': 0x10212C00,
            'tmp_addr': 0x110001A0,
            'brom_g_bounds_check': (
                (0x0010276C, 0x00000000),
                (0x00105704, 0x00000000),
            ),
            'brom_g_da_verified': 0x001030BC,
        },
        0x0321: {
            'name': "MT6735",
            'brom': (0x00000000, 0x10000),
            'sram': (0x00100000, 0x10000),
            'l2_sram': (0x00200000, 0x40000),
            'toprgu': (0x10212000, 0x1000),
            'efusec': (0x10206000, 0x1000),
            'usbdl': 0x10000818,
            'cqdma_base': 0x10217C00,
            'tmp_addr': 0x110001A0,
            'brom_g_bounds_check': (
                (0x00102760, 0x00000000),
                (0x00105704, 0x00000000),
            ),
            'brom_g_da_verified': 0x001030C0,
        },
        0x0335: {
            'name': "MT6737M",
            'brom': (0x00000000, 0x10000),
            'sram': (0x00100000, 0x10000),
            'l2_sram': (0x00200000, 0x40000),
            'toprgu': (0x10212000, 0x1000),
            'efusec': (0x10206000, 0x1000),
            'usbdl': 0x10000818,
            'cqdma_base': 0x10217C00,
            'tmp_addr': 0x110001A0,
            'brom_g_bounds_check': (
                (0x00102760, 0x00000000),
                (0x00105704, 0x00000000),
            ),
            'brom_g_da_verified': 0x001030C0,
        },
        0x0788: {
            'name': "MT8183",
            'brom': (0x00000000, 0), # TODO: Find out how large the BROM is.
            'sram': (0x00100000, 0x20000),
            'l2_sram': (0x00200000, 0x80000),
            'toprgu': (0x10007000, 0x1000),
            'efusec': (0x11F10000, 0x1000),
        },
        0x8163: {
            'name': "MT8163",
            'brom': (0x00000000, 0x14000),
            'sram': (0x00100000, 0x10000),
            'l2_sram': (0x00200000, 0x40000),
            'toprgu': (0x10007000, 0x1000),
            'efusec': (0x10206000, 0x1000),
            'usbdl': 0x10202050,
            'cqdma_base': 0x10212C00,
            'tmp_addr': 0x110001A0,
            'brom_g_bounds_check': (
                (0x00102868, 0x00000000),
                (0x001072DC, 0x00000000),
            ),
            'brom_g_da_verified': 0x001031D0,
        },
    }

    def __init__(self, port, timeout=1, write_timeout=1, debug=False):
        self.debug = debug
        self.ser = serial.Serial(port, timeout=timeout, write_timeout=write_timeout)
        hw_code = self.cmd_get_hw_code()
        self.soc = self.socs[hw_code]
        print("{} detected!".format(self.soc['name']))

    def _send_bytes(self, data, echo=True):
        data = bytes(data)
        if self.debug:
            print("-> {}".format(binascii.b2a_hex(data)))
        self.ser.write(data)
        if echo:
            echo_data = self.ser.read(len(data))
            if self.debug:
                print("<- {}".format(binascii.b2a_hex(echo_data)))
            if echo_data != data:
                raise EchoBytesMismatchException

    def _recv_bytes(self, count):
        data = self.ser.read(count)
        if self.debug:
            print("<- {}".format(binascii.b2a_hex(data)))
        if len(data) != count:
            raise NotEnoughDataException
        return bytes(data)

    def get_word(self):
        #Read a big-endian 16-bit integer from the serial port.
        return struct.unpack('>H', self._recv_bytes(2))[0]

    def put_word(self, word):
        #Write a big-endian 16-bit integer to the serial port.
        self._send_bytes(struct.pack('>H', word))

    def get_dword(self):
        #Read a big-endian 32-bit integer from the serial port.
        return struct.unpack('>I', self._recv_bytes(4))[0]

    def put_dword(self, dword):
        #Write a big-endian 32-bit integer to the serial port.
        self._send_bytes(struct.pack('>I', dword))

    def cmd_C8(self, subcommand):
        subcommands = {
            'B0': 0xB0,
            'B1': 0xB1,
            'B2': 0xB2,
            'B3': 0xB3,
            'B4': 0xB4,
            'B5': 0xB5,
            'B6': 0xB6,
            'B7': 0xB7,
            'B8': 0xB8,
            'B9': 0xB9,
            'BA': 0xBA,
            'C0': 0xC0,
            'C1': 0xC1,
            'C2': 0xC2,
            'C3': 0xC3,
            'C4': 0xC4,
            'C5': 0xC5,
            'C6': 0xC6,
            'C7': 0xC7,
            'C8': 0xC8,
            'C9': 0xC9,
            'CA': 0xCA,
            'CB': 0xCB,
            'CC': 0xCC,
        }
        self._send_bytes([self.commands['CMD_C8']])
        self._send_bytes([subcommands[subcommand]])
        sub_data = struct.unpack('B', self._recv_bytes(1))[0]

        status = self.get_word()
        if status != 0:
            raise ProtocolError(status)

        return sub_data

    def cmd_read32(self, addr, word_count):
        #Read 32-bit words starting at an address.
        #addr: The 32-bit starting address as an int.
        #word_count: The number of words to read as an int.
        words = []

        self._send_bytes([self.commands['CMD_READ32']])
        self.put_dword(addr)
        self.put_dword(word_count)

        status = self.get_word()
        if status != 0:
            raise ProtocolError(status)

        for i in range(word_count):
            words.append(self.get_dword())

        status = self.get_word()
        if status != 0:
            raise ProtocolError(status)

        return words

    def cmd_write32(self, addr, words):
        #Write 32 bit words starting at an address.
        #addr: A 32-bit address as an int.
        #words: A list of 32-bit ints to write starting at address addr.
        self._send_bytes([self.commands['CMD_WRITE32']])
        self.put_dword(addr)
        self.put_dword(len(words))

        status = self.get_word()
        if status > 0xff:
            raise ProtocolError(status)

        for word in words:
            self.put_dword(word)

        status = self.get_word()
        if status > 0xff:
            raise ProtocolError(status)

    def cmd_jump_da(self, addr):
        self._send_bytes([self.commands['CMD_JUMP_DA']])
        self.put_dword(addr)

        status = self.get_word()
        if status > 0xff:
            raise ProtocolError(status)

    def cmd_jump_bl(self):
        self._send_bytes([self.commands['CMD_JUMP_BL']])

        status = self.get_word()
        if status > 0xff:
            raise ProtocolError(status)

    def cmd_send_da(self, load_addr, data, sig_length=0, print_speed=False):
        self._send_bytes([self.commands['CMD_SEND_DA']])
        self.put_dword(load_addr)
        self.put_dword(len(data))
        self.put_dword(sig_length)

        status = self.get_word()
        if status > 0xff:
            raise ProtocolError(status)

        calc_checksum = 0
        padded_data = data
        if len(padded_data) % 2 != 0:
            padded_data += b'\0'
        for i in range(0, len(padded_data), 2):
            calc_checksum ^= struct.unpack_from('<H', padded_data, i)[0]

        start_time = time.time()
        self._send_bytes(data, echo=False)
        end_time = time.time()

        remote_checksum = self.get_word()

        if remote_checksum != calc_checksum:
            raise ChecksumError("Checksum mismatch: Expected 0x{:04x}, got 0x{:04x}.".format(calc_checksum, remote_checksum))

        status = self.get_word()
        if status > 0xff:
            raise ProtocolError(status)

        if print_speed:
            elapsed = end_time - start_time
            print("Sent {} DA bytes in {:.6f} seconds ({} bytes per second).".format(len(data), elapsed, int(len(data)/elapsed)))

    def cmd_get_target_config(self):
        self._send_bytes([self.commands['CMD_GET_TARGET_CONFIG']])

        target_config = self.get_dword()
        print("Target config: 0x{:08X}".format(target_config))
        print("\tSBC enabled: {}".format(True if (target_config & 0x1) else False))
        print("\tSLA enabled: {}".format(True if (target_config & 0x2) else False))
        print("\tDAA enabled: {}".format(True if (target_config & 0x4) else False))

        status = self.get_word()
        if status > 0xff:
            raise ProtocolError(status)

    def cmd_uart1_log_enable(self):
        self._send_bytes([self.commands['CMD_UART1_LOG_EN']])

        status = self.get_word()
        if status != 0:
            raise ProtocolError(status)

    def cmd_uart1_set_baud(self, baud):
        self._send_bytes([self.commands['CMD_UART1_SET_BAUD']])
        self.put_dword(baud)

        status = self.get_word()
        if status != 0:
            raise ProtocolError(status)

    def cmd_get_brom_log(self):
        self._send_bytes([self.commands['CMD_GET_BROM_LOG']])
        length = self.get_dword()
        log_bytes = self._recv_bytes(length)

        return log_bytes

    def scmd_get_me_id(self):
        self._send_bytes([self.commands['SCMD_GET_ME_ID']])
        length = self.get_dword()
        me_id = self._recv_bytes(length)

        status = self.get_word()
        if status != 0:
            raise ProtocolError(status)

        return me_id

    def cmd_get_hw_sw_ver(self):
        self._send_bytes([self.commands['CMD_GET_HW_SW_VER']])
        hw_subcode = self.get_word()
        hw_ver = self.get_word()
        sw_ver = self.get_word()

        status = self.get_word()
        if status != 0:
            raise ProtocolError(status)

        return (hw_subcode, hw_ver, sw_ver)

    def cmd_get_hw_code(self):
        self._send_bytes([self.commands['CMD_GET_HW_CODE']])
        hw_code = self.get_word()

        status = self.get_word()
        if status != 0:
            raise ProtocolError(status)

        return hw_code

    def cqdma_read32(self, addr, word_count):
        #Read 32-bit words starting at an address, using the CQDMA peripheral.
        #addr: The 32-bit starting address as an int.
        #word_count: The number of words to read as an int.

        tmp_addr = self.soc['tmp_addr']
        cqdma_base = self.soc['cqdma_base']

        words = []
        for i in range(word_count):
            # Set DMA source address.
            self.cmd_write32(cqdma_base+0x1C, [addr+i*4])
            # Set DMA destination address.
            self.cmd_write32(cqdma_base+0x20, [tmp_addr])
            # Set DMA transfer length in bytes.
            self.cmd_write32(cqdma_base+0x24, [4])
            # Start DMA transfer.
            self.cmd_write32(cqdma_base+0x08, [0x00000001])
            # Wait for transaction to finish.
            while True:
                if (self.cmd_read32(cqdma_base+0x08, 1)[0] & 1) == 0:
                    break
            # Read word from tmp_addr.
            words.extend(self.cmd_read32(tmp_addr, 1))

        return words

    def cqdma_write32(self, addr, words):
        #Write 32 bit words starting at an address, using the CQDMA peripheral.
        #addr: A 32-bit address as an int.
        #words: A list of 32-bit ints to write starting at address addr.

        tmp_addr = self.soc['tmp_addr']
        cqdma_base = self.soc['cqdma_base']

        for i in range(len(words)):
            # Write word to tmp_addr.
            self.cmd_write32(tmp_addr, [words[i]])
            # Set DMA source address.
            self.cmd_write32(cqdma_base+0x1C, [tmp_addr])
            # Set DMA destination address.
            self.cmd_write32(cqdma_base+0x20, [addr+i*4])
            # Set DMA transfer length in bytes.
            self.cmd_write32(cqdma_base+0x24, [4])
            # Start DMA transfer.
            self.cmd_write32(cqdma_base+0x08, [0x00000001])
            # Wait for transaction to finish.
            while True:
                if (self.cmd_read32(cqdma_base+0x08, 1)[0] & 1) == 0:
                    break
            # Write dummy word to tmp_addr for error detection.
            self.cmd_write32(tmp_addr, [0xc0ffeeee])

    def memory_read(self, addr, count, cqdma=False, print_speed=False):
        #Read a range of memory to a byte array.

        #addr: A 32-bit address as an int.
        #count: The length of data to read, in bytes.
        word_count = count//4
        if (count % 4) > 0:
            word_count += 1

        words = []
        start_time = time.time()
        if cqdma:
            words = self.cqdma_read32(addr, word_count)
        else:
            words = self.cmd_read32(addr, word_count)
        end_time = time.time()

        data = b''
        for word in words:
            data += struct.pack('<I', word)
        data = data[:count]

        if print_speed:
            elapsed = end_time - start_time
            print("Read {} bytes in {:.6f} seconds ({} bytes per second).".format(len(data), elapsed, int(len(data)/elapsed)))

        return data

    def memory_write(self, addr, data, cqdma=False, print_speed=False):
        #Write a byte array to a range of memory.
        #addr: A 32-bit address as an int.
        #data: The data to write.
        data = bytes(data)

        # Pad the byte array.
        padded_data = data
        remaining_bytes = (len(padded_data) % 4)
        if remaining_bytes > 0:
            padded_data += b'\0' * (4 - remaining_bytes)

        words = []
        for i in range(0, len(padded_data), 4):
            words.append(struct.unpack_from('<I', padded_data, i)[0])

        start_time = time.time()
        if cqdma:
            self.cqdma_write32(addr, words)
        else:
            self.cmd_write32(addr, words)
        end_time = time.time()

        if print_speed:
            elapsed = end_time - start_time
            print("Wrote {} bytes in {:.6f} seconds ({} bytes per second).".format(len(data), elapsed, int(len(data)/elapsed)))

    def wdt_reset(self):
        self.cmd_write32(self.soc['toprgu'][0], [0x22000000 | 0x10 | 0x4])
        time.sleep(0.001)
        self.cmd_write32(self.soc['toprgu'][0] + 0x14, [0x1209])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=str, help="The serial port you want to connect to.")
    args = parser.parse_args()

    usbdl = UsbDl(args.port, debug=False)

    # Get the security configuration of the target.
    usbdl.cmd_get_target_config()

    # Disable WDT.
    print("Disabling WDT...")
    usbdl.cmd_write32(usbdl.soc['toprgu'][0], [0x22000000])

    # Dump efuses to file.
    print("Dumping efuses...")
    efuses = usbdl.memory_read(usbdl.soc['efusec'][0], usbdl.soc['efusec'][1])
    efuse_file = open("{}-efuses.bin".format(usbdl.soc['name'].lower()), 'wb')
    efuse_file.write(efuses)
    efuse_file.close()

    # Print a string to UART0.
    for byte in "Hello, there!\r\n".encode('utf-8'):
        usbdl.cmd_write32(0x11002000, [byte])

    try:
        # The C8 B1 command disables caches.
        usbdl.cmd_C8('B1')
    except:
        # The C8 command is not available in Preloader mode.
        print("Error: Not in BROM DL mode. Attempting to reboot into BROM DL mode...")
        timeout = 60 # 0x3fff is no timeout. Less than that is timeout in seconds.
        usbdl_flag = (0x444C << 16) | (timeout << 2) | 0x00000001 # USBDL_BIT_EN
        usbdl.cmd_write32(usbdl.soc['usbdl'] + 0x00, [usbdl_flag])  # USBDL_FLAG/BOOT_MISC0

        # Make sure USBDL_FLAG is not reset by the WDT.
        usbdl.cmd_write32(usbdl.soc['usbdl'] + 0x20, [0xAD98])  # MISC_LOCK_KEY
        usbdl.cmd_write32(usbdl.soc['usbdl'] + 0x28, [0x00000001])  # RST_CON
        usbdl.cmd_write32(usbdl.soc['usbdl'] + 0x20, [0])  # MISC_LOCK_KEY

        # WDT reset.
        usbdl.wdt_reset()

        # Exit because we won't be able to talk to the device any more.
        sys.exit(0)

    # Assume we have to use the CQDMA to access restricted memory.
    use_cqdma = True

    # Check if the bounds check method is available.
    if usbdl.soc.get('brom_g_bounds_check', False):
        # Disable bounds check.
        for (addr, data) in usbdl.soc['brom_g_bounds_check']:
            usbdl.cqdma_write32(addr, [data])

        # We can use normal read32/write32 commands now.
        use_cqdma = False

    # NOTE: Using the CQDMA method to dump a large (>4kB) chunk of memory,
    # like the entire BROM, will almost certainly fail and cause the CPU to
    # reset. To work around this, try dumping the memory in smaller chunks,
    # like 1kB, and saving them to disk, then reboot the SoC into BROM mode
    # again and dump the next chunk until you've dumped the memory you're
    # interested in.

    # Dump BROM.
    print("Dumping BROM...")
    brom = usbdl.memory_read(usbdl.soc['brom'][0], usbdl.soc['brom'][1], cqdma=use_cqdma, print_speed=True)
    if len(brom) != usbdl.soc['brom'][1]:
        print("Error: Failed to dump entire BROM.")
        sys.exit(1)

    brom_file = open("{}-brom.bin".format(usbdl.soc['name'].lower()), 'wb')
    brom_file.write(brom)
    brom_file.close()

    # Dump SRAM.
    print("Dumping SRAM...")
    sram = usbdl.memory_read(usbdl.soc['sram'][0], usbdl.soc['sram'][1], cqdma=use_cqdma, print_speed=True)
    sram_file = open("{}-sram.bin".format(usbdl.soc['name'].lower()), 'wb')
    sram_file.write(sram)
    sram_file.close()

    # Dump L2 SRAM.
    print("Dumping L2 SRAM...")
    l2_sram = usbdl.memory_read(usbdl.soc['l2_sram'][0], usbdl.soc['l2_sram'][1], cqdma=use_cqdma, print_speed=True)
    l2_sram_file = open("{}-l2-sram.bin".format(usbdl.soc['name'].lower()), 'wb')
    l2_sram_file.write(l2_sram)
    l2_sram_file.close()

    # Code parameters.
    binary = open("demo/mode-switch/mode-switch.bin", 'rb').read()
    load_addr = 0x00200000
    thumb_mode = False

    # Load executable.
    print("Loading executables...")
    usbdl.memory_write(load_addr, binary, cqdma=use_cqdma, print_speed=True)
    usbdl.memory_write(0x00201000, open("demo/hello-aarch64/hello-aarch64.bin", 'rb').read(), cqdma=use_cqdma, print_speed=True)

    # Mark DA as verified.
    if usbdl.soc.get('brom_g_da_verified', False):
        if use_cqdma:
            usbdl.cqdma_write32(usbdl.soc['brom_g_da_verified'], [1])
        else:
            usbdl.cmd_write32(usbdl.soc['brom_g_da_verified'], [1])
    else:
        print("Error: No DA verification address specified, exiting...")
        sys.exit(1)

    # Jump to executable.
    print("Jumping to executable...")
    if thumb_mode:
        load_addr |= 1
    usbdl.cmd_jump_da(load_addr)
'''

# Preloader

'''
#!/usr/bin/env python3

#Create "preloader" images suitable for booting on MediaTek platforms.
#
#Provide an ARMv7-A/ARMv8-A (AArch32-only) binary as an input, and this
#tool will convert it into an image that, depending on your selected
#options, will be able to be booted from either eMMC flash or an SD card.
#
#For example, to create an eMMC image, run:
#
#    ./make_image.py -b eMMC -o preloader-emmc.img code.bin
#
#This can be written to the eMMC BOOT0 hardware partition using
#MediaTek's SPFT utility, the same way any other preloader is written.
#
#To create an SD image, run:
#
#    ./make_image.py -b SD -o preloader-sd.img code.bin
#
#To write the image to an SD card, run:
#
#    sudo dd if=preloader-sd.img of=/dev/DEVICE bs=2048 seek=1
#
#Where `/dev/DEVICE` is the path to your SD card, e.g., `/dev/sdX` or
#`/dev/mmcblkX`.
#
#This command writes the SD preloader to byte offset 2048 (LBA 4,
#512-byte blocks) on the card, so if you want to create a partition table
#on the card, you MUST you an MBR (DOS) scheme--writing a GPT after
#flashing the preloader will likely overwrite the preloader, and writing
#the preloader after creating the GPT will likely corrupt the GPT. It is
#equally important to ensure that your first partition starts at sector
#(LBA) 4096--this will give enough space for the largest possible
#preloader size (1 MiB, the size of the L2 SRAM on some higher-end SoCs),
#plus it will ensure your partitions are nicely aligned. 4096 is largely
#an arbitrary number, since the smallest LBA number to avoid the first
#partition overwriting the preloader is 2052 (LBA 4 + 1 MiB / 512 B), so
#in theory you could use that (or an even smaller number for devices with
#a 256 KiB L2 SRAM), but 4096 is a nice power of 2 so I like that better.

import argparse
import enum
import hashlib
import struct


class code_arch(enum.Enum):
    aarch32 = enum.auto()
    aarch64 = enum.auto()

class flash_device(enum.Enum):
    EMMC = enum.auto()
    SD = enum.auto()

class gfh_type(enum.Enum):
    FILE_INFO = enum.auto(),
    BL_INFO = enum.auto(),
    ANTI_CLONE = enum.auto(),
    BL_SEC_KEY = enum.auto(),
    BROM_CFG = enum.auto(),
    BROM_SEC_CFG = enum.auto(),


def gen_gfh_header(type, version):
    magic = b'MMM'

    size = {
        gfh_type.FILE_INFO: 56,
        gfh_type.BL_INFO: 12,
        gfh_type.ANTI_CLONE: 20,
        gfh_type.BL_SEC_KEY: 532,
        gfh_type.BROM_CFG: 100,
        gfh_type.BROM_SEC_CFG: 48,
    }.get(type)
    if size == None:
        raise ValueError("Unknown gfh_type: {}".format(type))

    type = {
        gfh_type.FILE_INFO: 0,
        gfh_type.BL_INFO: 1,
        gfh_type.ANTI_CLONE: 2,
        gfh_type.BL_SEC_KEY: 3,
        gfh_type.BROM_CFG: 7,
        gfh_type.BROM_SEC_CFG: 8,
    }.get(type)

    h = struct.pack('3s', magic)
    h += struct.pack('B', version)
    h += struct.pack('<H', size)
    h += struct.pack('<H', type)

    return h

def gen_gfh_file_info(file_type, flash_dev, offset, base_addr, start_addr, max_size, payload_size):
    identifier = b'FILE_INFO'
    file_ver = 1
    sig_type = 1  # SIG_PHASH
    load_addr = base_addr - offset
    sig_len = 32  # SHA256
    file_len = offset + payload_size + sig_len
    jump_offset = start_addr - load_addr
    attr = 1

    file_info = gen_gfh_header(gfh_type.FILE_INFO, 1)
    file_info += struct.pack('12s', identifier)
    file_info += struct.pack('<I', file_ver)
    file_info += struct.pack('<H', file_type)
    file_info += struct.pack('B', flash_dev)
    file_info += struct.pack('B', sig_type)
    file_info += struct.pack('<I', load_addr)
    file_info += struct.pack('<I', file_len)
    file_info += struct.pack('<I', max_size)
    file_info += struct.pack('<I', offset)
    file_info += struct.pack('<I', sig_len)
    file_info += struct.pack('<I', jump_offset)
    file_info += struct.pack('<I', attr)

    return file_info

def gen_gfh_bl_info():
    bl_info = gen_gfh_header(gfh_type.BL_INFO, 1)
    bl_info += struct.pack('<I', 1)

    return bl_info

def gen_gfh_brom_cfg(arch):
    brom_cfg = gen_gfh_header(gfh_type.BROM_CFG, 3)
    # TODO: Make this configurable.
    brom_cfg += bytes.fromhex("9001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000881300000000000000000000")

    if arch == code_arch.aarch64:
        brom_cfg = bytearray(brom_cfg)

        # Set the flag.
        flags = struct.unpack_from('<I', brom_cfg, 8)[0]
        flags |= 1 << 12
        struct.pack_into('<I', brom_cfg, 8, flags)

        # Set the magic value.
        brom_cfg[0x55] = 0x64

        brom_cfg = bytes(brom_cfg)

    return brom_cfg

def gen_gfh_bl_sec_key():
    bl_sec_key = gen_gfh_header(gfh_type.BL_SEC_KEY, 1)
    bl_sec_key += bytes(bytearray(524))

    return bl_sec_key

def gen_gfh_anti_clone():
    anti_clone = gen_gfh_header(gfh_type.ANTI_CLONE, 1)
    anti_clone += bytes(bytearray(12))

    return anti_clone

def gen_gfh_brom_sec_cfg():
    brom_sec_cfg = gen_gfh_header(gfh_type.BROM_SEC_CFG, 1)
    brom_sec_cfg += struct.pack('<I', 3)
    brom_sec_cfg += bytes(bytearray(36))

    return brom_sec_cfg

def gen_image(boot_device, payload, payload_arch):
    # Header
    identifier = {
        flash_device.EMMC: b'EMMC_BOOT',
        flash_device.SD: b'SDMMC_BOOT',
    }.get(boot_device)
    if identifier == None:
        raise ValueError("Unknown boot_device: {}".format(boot_device))

    version = 1

    dev_rw_unit = {
        flash_device.EMMC: 512,
        flash_device.SD: 512,
    }.get(boot_device)

    header = struct.pack('12s', identifier)
    header += struct.pack('<I', version)
    header += struct.pack('<I', dev_rw_unit)

    assert(len(header) <= dev_rw_unit)
    padding_length = dev_rw_unit - len(header)
    header += bytes(bytearray(padding_length))

    # Boot ROM layout
    identifier = b'BRLYT'
    version = 1
    gfh_block_offset = 4
    # Must be >=2 to account for the device header and boot ROM layout blocks.
    assert(gfh_block_offset >= 2)
    boot_region_addr = {
        flash_device.EMMC: dev_rw_unit * gfh_block_offset,
        flash_device.SD: dev_rw_unit * gfh_block_offset + 2048,  # SDMMC_BOOT is flashed to byte offset 2048 on the SD card.
    }.get(boot_device)
    max_preloader_size = 0x40000  # 0x40000 is the size of the L2 SRAM, so the maximum possible size of the preloader.
    main_region_addr = max_preloader_size + boot_region_addr

    layout = struct.pack('8s', identifier)
    layout += struct.pack('<I', version)
    layout += struct.pack('<I', boot_region_addr)
    layout += struct.pack('<I', main_region_addr)

    # bootloader_descriptors[0]
    bl_exist_magic = b'BBBB'
    bl_dev = {
        flash_device.EMMC: 5,
        flash_device.SD: 8,
    }.get(boot_device)
    bl_type = 1  # ARM_BL
    bl_begin_addr = boot_region_addr
    bl_boundary_addr = main_region_addr
    bl_attribute = 1

    layout += struct.pack('4s', bl_exist_magic)
    layout += struct.pack('<H', bl_dev)
    layout += struct.pack('<H', bl_type)
    layout += struct.pack('<I', bl_begin_addr)
    layout += struct.pack('<I', bl_boundary_addr)
    layout += struct.pack('<I', bl_attribute)

    layout_max_size = dev_rw_unit * (gfh_block_offset - 1)
    assert(len(layout) <= layout_max_size)
    padding_length = layout_max_size - len(layout)
    layout += bytes(bytearray(padding_length))

    # GFH image
    offset = 0x300
    base_addr = 0x201000
    start_addr = base_addr
    image = gen_gfh_file_info(bl_type, bl_dev, offset, base_addr, start_addr, max_preloader_size, len(payload))
    image += gen_gfh_bl_info()
    image += gen_gfh_brom_cfg(payload_arch)
    image += gen_gfh_bl_sec_key()
    image += gen_gfh_anti_clone()
    image += gen_gfh_brom_sec_cfg()

    assert(len(image) <= offset)
    padding_length = offset - len(image)
    image += bytes(bytearray(padding_length))

    image += payload

    image += hashlib.sha256(image).digest()

    return header + layout + image

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input binary.")
    parser.add_argument("-o", "--output", type=str, default="preloader.img", help="Output image.")
    parser.add_argument("-b", "--boot-device", type=str, choices=["eMMC", "SD"], default="eMMC", help="Boot device.")
    parser.add_argument("-a", "--arch", type=str, choices=["aarch32", "aarch64"], default="aarch32", help="Code architecture. Choose \"aarch32\" if you're booting 32-bit ARM code, \"aarch64\" for 64-bit ARM code.")
    args = parser.parse_args()

    binary = open(args.input, 'rb').read()
    padding_length = 4 - (len(binary) % 4)
    if padding_length != 4:
        binary += bytes(bytearray(padding_length))

    boot_device = {
        "eMMC": flash_device.EMMC,
        "SD": flash_device.SD,
    }.get(args.boot_device)

    arch = {
        "aarch32": code_arch.aarch32,
        "aarch64": code_arch.aarch64,
    }.get(args.arch)

    image = gen_image(boot_device, binary, arch)

    output = open(args.output, 'wb')
    output.write(image)
    output.close()

'''
