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

def hook_mem_read(uc,access,address,size,value,user_data):
    pc = uc.reg_read(UC_ARM_REG_PC)
    #if address<0xF000000:
    #    #print("READ of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    #    #return True
    if address == 0x10007000:
        print("WD 0x10007000")
        return True
    elif address == 0x11002014:
        #print("UART0: %08X" % pc)
        uc.mem_write(0x11002014,pack("<I",0x20))
        return True
    elif address == 0x11002000:
        uc.mem_write(0x11002014,pack("<I",0))
        print("UART1 R")
        return True
    elif 0x102000>address>=0x100FF0:
        val=unpack("<I",uc.mem_read(address,4))[0]
        #print("RHeap: %08X A:%08X V:%08X" % (pc,address,val))
        return True

buffer=bytearray()

def hook_mem_write(uc,access,address,size,value,user_data):
    global buffer
    pc = uc.reg_read(UC_ARM_REG_PC)
    if 0x40000>address>=0x30000:
        return True
    if address == 0x10007000:
        print("WD: 0x10007000")
        return True
    if address == 0x11002000:
        r0 = uc.reg_read(UC_ARM_REG_R0)
        if r0==0xa:
            print("UART: "+buffer.decode('utf-8'))
            buffer=bytearray()
        else:
            buffer.append(r0)
        return True
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
    #bootrom = open("/home/bjk/Projects/bootrom/mtk/mt8173_8172.bin", "rb").read()
    #bootrom = open("/home/bjk/Projects/bootrom/mtk/mt8163.bin", "rb").read()
    bootrom = open("/home/bjk/Projects/bootrom/mtk/mt6737_wd10216000_335.bin", "rb").read()
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    reg = ARMRegisters(mu)
    mu.mem_map(0x0, 0x400000)
    mu.mem_write(0x0, bootrom)
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
        sys.exit(0)
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

    replace_function(0x42a2,send_usb_response)
    replace_function(0x95ea,usbdl_put_data)
    replace_function(0x9564,usbdl_get_data)
    #replace_function(0x100E40,printf)

    mu.mem_map(0x10000000, 0x1000000) #WD
    mu.mem_map(0x11000000, 0x20000) # Uart
    #mu.mem_map(0x100FF0, 0x20000)  # Heap

    #Main EDL emulation
    logger.info("Emulating EDL")
    mu.emu_start(0x100A00,0x100AE4,0,0) #handle_xml
    logger.info("Emulation done.")


if __name__=="__main__":
    main()
