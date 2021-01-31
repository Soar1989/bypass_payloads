#!/usr/bin/env python3

import logging
import sys
import Library.logcolor
import hashlib
logger = logging.getLogger(__name__)
# debuglevel=logging.DEBUG
debuglevel = logging.INFO
logging.basicConfig(format='%(funcName)20s:%(message)s', level=debuglevel)

from unicorn import *
from unicorn.arm_const import *
import time
import os
from struct import pack,unpack
from Library.emulation_tools import emulation_tools
from binascii import hexlify

class ARMRegisters(dict):
    def __init__(self, mu):
        super().__init__()
        self.mu=mu

    def __setitem__(self, key, value):
        if isinstance(key, str):
            key = key.casefold()
            self.mu.reg_write(eval("UC_ARM_REG_"+key.upper()),value)
        super().__setitem__(key, value)

    def __getitem__(self, key):
        if isinstance(key, str):
            key = key.casefold()
            value=self.mu.reg_read(eval("UC_ARM_REG_"+key.upper()))
            super().__setitem__(key, value)
        return super().__getitem__(key)

buffer=bytearray()
data=""

def hook_mem_read(uc,access,address,size,value,user_data):
    global data
    pc = uc.reg_read(UC_ARM_REG_PC)
    #if address<0xF000000:
    #    #print("READ of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    #    #return True
    if address == 0x10007000:
        print("WD 0x10007000")
        data+="WD 0x10007000"
        return True
    elif address == 0x11002014:
        #print("UART0: %08X" % pc)
        uc.mem_write(0x11002014,pack("<I",0x20))
        return True
    elif address == 0x11002000:
        uc.mem_write(0x11002014,pack("<I",0))
        print("UART1 R")
        return True
    elif address == 0x11003014:
        #print("UART0: %08X" % pc)
        uc.mem_write(0x11003014,pack("<I",0x20))
        return True
    elif address == 0x11003000:
        uc.mem_write(0x11003014,pack("<I",0))
        print("UART1 R")
        return True
    elif address == 0x11005014:
        #print("UART0: %08X" % pc)
        uc.mem_write(0x11005014,pack("<I",0x20))
        return True
    elif address == 0x11005000:
        uc.mem_write(0x11005014,pack("<I",0))
        print("UART1 R")
        return True
    elif 0x102000>address>=0x100FF0:
        val=unpack("<I",uc.mem_read(address,4))[0]
        #print("RHeap: %08X A:%08X V:%08X" % (pc,address,val))
        return True



def hook_mem_write(uc,access,address,size,value,user_data):
    global buffer
    global data
    pc = uc.reg_read(UC_ARM_REG_PC)
    if 0x40000>address>=0x30000:
        return True
    if address == 0x10007000:
        data+="WD: 0x10007000"
        print("WD: 0x10007000")
        return True
    elif address == 0x10212000:
        data+="WD: 0x10212000"
        print("WD: 0x10212000")
        return True
    elif address == 0x11002000:
        r0 = uc.reg_read(UC_ARM_REG_R0)
        if r0==0xa:
            print("UART: "+buffer.decode('utf-8'))
            data+=buffer.decode('utf-8')
            buffer=bytearray()
        else:
            buffer.append(r0)
        return True
    elif address == 0x11003000:
        r0 = uc.reg_read(UC_ARM_REG_R0)
        if r0==0xa:
            print("UART: "+buffer.decode('utf-8'))
            data+=buffer.decode('utf-8')
            buffer=bytearray()
        else:
            buffer.append(r0)
        return True
    elif address == 0x11005000:
        r0 = uc.reg_read(UC_ARM_REG_R0)
        if r0==0xa:
            print("UART: "+buffer.decode('utf-8'))
            data+=buffer.decode('utf-8')
            buffer=bytearray()
        else:
            buffer.append(r0)
        return True
    else:
        print("Write : %08X - %08X" % (address, value))
    if address>=0x100FF0:
        val=unpack("<I",uc.mem_read(address,4))[0]
        #print("WHeap: %08X A:%08X V:%08X" % (pc,address,val))
        return True
    elif address==0x1027DC:
        print("SEC_REG pass")
        return True

def hook_code(uc,access,address,size):
    pc = uc.reg_read(UC_ARM_REG_PC)
    #print("PC %08X" % pc)
    return True

def hook_mem_invalid(uc, access, address, size, value, user_data):
    pc = uc.reg_read(UC_ARM_REG_PC)
    if access == UC_MEM_WRITE:
        info=("invalid WRITE of 0x%x at 0x%X, data size = %u, data value = 0x%x" % (address, pc, size, value))
    if access == UC_MEM_READ:
        info=("invalid READ of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_FETCH:
        info=("UC_MEM_FETCH of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_READ_UNMAPPED:
        info=("UC_MEM_READ_UNMAPPED of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_WRITE_UNMAPPED:
        info=("UC_MEM_WRITE_UNMAPPED of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_FETCH_UNMAPPED:
        info=("UC_MEM_FETCH_UNMAPPED of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_WRITE_PROT:
        info=("UC_MEM_WRITE_PROT of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_FETCH_PROT:
        info=("UC_MEM_FETCH_PROT of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_FETCH_PROT:
        info=("UC_MEM_FETCH_PROT of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_READ_AFTER:
        info=("UC_MEM_READ_AFTER of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    print(info)
    return False

def main():
    pfilename = os.path.join("payloads", "generic_patcher_payload.bin")
    payload = open(pfilename, "rb").read()
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    reg = ARMRegisters(mu)
    mu.mem_map(0x0, 0x400000)
    mu.mem_write(0x100A00, payload)
    def replace_function(address,callback):
        def hook_code(uc, address, size, user_data):
            logger.debug(">>> Installed hook at 0x%x, instruction size = 0x%x" % (address, size))
            ret = user_data(reg)
            uc.reg_write(UC_ARM_REG_R0, ret)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        mu.hook_add(UC_HOOK_CODE, hook_code, user_data=callback, begin=address, end=address)

    def monitor_function(address,callback):
        def hook_code(uc, address, size, user_data):
            logger.debug(">>> Installed monitor at 0x%x, instruction size = 0x%x" % (address, size))
            user_data(reg)
        mu.hook_add(UC_HOOK_CODE, hook_code, user_data=callback, begin=address, end=address)

    def send_usb_response(regs):
        pc = reg["LR"]
        print("send_usb_response %08X" % pc)
        return 0

    def usbdl_put_data(regs):
        pc = reg["LR"]
        print("usbdl_put_data %08X" % pc)
        return 0

    def usbdl_get_data(regs):
        pc=reg["LR"]
        print("usbdl_get_data %08X" % pc)
        reg["LR"]=-1
        mu.emu_stop()
        return 0

    def printf(regs):
        pc=reg["LR"]
        r0=reg["R0"]
        data=uc.mem_read(r0,20)
        print("printf %08X : %s" % data)
        sys.exit(0)
        return 0

    #Init values
    reg["SP"]=0x40000  # Stack from start
    #mu.hook_add(UC_HOOK_BLOCK, hook_block)
    mu.hook_add(UC_HOOK_MEM_INVALID, hook_mem_invalid)
    mu.hook_add(UC_HOOK_CODE, hook_code, begin=0, end=-1)
    mu.hook_add(UC_HOOK_MEM_READ, hook_mem_read)
    mu.hook_add(UC_HOOK_MEM_WRITE, hook_mem_write)
    mu.mem_map(0x10000000, 0x1000000) #WD
    mu.mem_map(0x11000000, 0x20000) # Uart
    #mu.mem_map(0x100FF0, 0x20000)  # Heap

    br={
        #"/home/bjk/Projects/bootrom/mtk/mt6768_707.bin":(0x2c2f,0xc173,0xc0e5,0x102A8c,0x102a94,0x10007000,0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt8695.bin": (0x55bb, 0xbed1, 0xbe4b, 0x102FBC, 0x0, 0x10007000,0x11003000),
        #"/home/bjk/Projects/bootrom/mtk/mt6737_wd10216000_335.bin":(0x42a3,0x95eb,0x9565,0x1026D4,0x0,0x10212000,0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt8173_8172.bin":(0x4c5f,0xa0c7,0xa041,0x1226e8,0x0,0x10007000,0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt8163.bin":(0x6d6f,0xc10f,0xc089,0x1027dc,0x0,0x10007000,0x11002000),
        "/home/bjk/Projects/bootrom/mtk/mt8127.bin":(0x62a1,0xb29b,0xb215,0x1027e4,0x0,0x10007000,0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt6873_886.bin": (0x53af, 0xea5b, 0xe9cd, 0x102b0c, 0x102b14, 0x10007000, 0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt6785.bin": (0x4C8F, 0xe287, 0xe1f9, 0x102acc, 0x102ad4, 0x10007000, 0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt6771_788.bin": (0x4DAF, 0xDE9F, 0xDE11, 0x102acc, 0x102ad4, 0x10007000, 0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt6765_766.bin": (0x2D2B, 0xBDA3, 0xBD15, 0x102a8c, 0x102a94, 0x10007000, 0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt6761_717.bin": (0x2CDF, 0xBC6F, 0xBBE1, 0x102a8c, 0x102a94, 0x10007000, 0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt6757_551.bin": (0x455f, 0x9C0F, 0x9B89, 0x1026E4, 0x0, 0x10007000, 0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt6750.bin": (0x449f, 0x9a4f, 0x99c9, 0x1026DC, 0x0, 0x10007000, 0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt6739_699.bin": (0x508B, 0xDEFF, 0xDE71, 0x102A8C, 0x102A94, 0x10007000, 0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt6735.bin": (0x4293, 0x95DB, 0x9555, 0x1026D4, 0x0, 0x10212000, 0x11002000),
        #"/home/bjk/Projects/bootrom/mtk/mt6580.bin": (0x62E5, 0xB5EF, 0xB569, 0x1026D8, 0x0, 0x10007000, 0x11005000),
    }



    for field in br:
        bootrom = open(field, "rb").read()
        mu.mem_write(0x0, bootrom)
        replace_function(br[field][0]-1,send_usb_response)
        replace_function(br[field][1]-1,usbdl_put_data)
        replace_function(br[field][2]-1,usbdl_get_data)

        #Main EDL emulation
        logger.info("Emulating EDL")
        try:
            mu.emu_start(0x100A00,-1,0,0) #handle_xml
        except:
            pass
        val1=hexlify(pack("<I",br[field][0])).decode('utf-8').upper()
        if val1 not in data:
            print("send_usb_response failed")
        val2=hexlify(pack("<I",br[field][1])).decode('utf-8').upper()
        if val2 not in data:
            print("usbdl_get_data failed")
        val3=hexlify(pack("<I",br[field][2])).decode('utf-8').upper()
        if val3 not in data:
            print("usbdl_put_data failed")
        val4=hexlify(pack("<I",br[field][3])).decode('utf-8').upper()
        if val4 not in data:
            print("sec_roffset failed")
        val4=hexlify(pack("<I",br[field][4])).decode('utf-8').upper()
        if val4 not in data:
            print("sec_roffset2 failed")
        val4="%08X" % br[field][5]
        if val4 not in data:
            print("wdt failed")

    logger.info("Emulation done.")


if __name__=="__main__":
    main()
