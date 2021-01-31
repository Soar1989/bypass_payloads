from heapq import *
from unicorn import *
from unicorn.arm64_const import *
import logging
import Library.logcolor
logger = logging.getLogger(__name__)
from struct import unpack

from Library.utils import elf

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

class Memory(dict):
    def __init__(self, mu):
        super().__init__()
        self.mu=mu

    def __setitem__(self, key, value):
        if isinstance(key, str):
            key = key.casefold()
            self.mu.mem_write(int(key,16),value)
        elif isinstance(key, int):
            self.mu.mem_write(key, value)

    def __getitem__(self, key):
        if isinstance(key, str):
            key = key.casefold()
            return unpack("<Q",self.mu.mem_read(int(key,16),8))[0]
        elif isinstance(key, int):
            return unpack("<Q",self.mu.mem_read(key,8))[0]

    def read(self, addr, length):
        return self.mu.mem_read(addr,length)

    def write(self, addr, value):
        return self.mu.mem_write(addr,value)

def hook_mem_invalid(uc, access, address, size, value, user_data):
    pc = uc.reg_read(UC_ARM64_REG_PC)
    if access == UC_MEM_WRITE:
        logger.debug("invalid WRITE of 0x%x at 0x%X, data size = %u, data value = 0x%x" % (address, pc, size, value))
    if access == UC_MEM_READ:
        logger.debug("invalid READ of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_FETCH:
        logger.debug("UC_MEM_FETCH of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_READ_UNMAPPED:
        logger.debug("UC_MEM_READ_UNMAPPED of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_WRITE_UNMAPPED:
        logger.debug("UC_MEM_WRITE_UNMAPPED of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_FETCH_UNMAPPED:
        logger.debug("UC_MEM_FETCH_UNMAPPED of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_WRITE_PROT:
        logger.debug("UC_MEM_WRITE_PROT of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_FETCH_PROT:
        logger.debug("UC_MEM_FETCH_PROT of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_FETCH_PROT:
        logger.debug("UC_MEM_FETCH_PROT of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    if access == UC_MEM_READ_AFTER:
        logger.debug("UC_MEM_READ_AFTER of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    return False


def hook_mem_read(uc, access, address, size, value, user_data):
    pc = uc.reg_read(UC_ARM64_REG_PC)
    if access == UC_MEM_READ:
        logger.debug("READ of 0x%x at 0x%X, data size = %u" % (address, pc, size))
    pass

# callback for tracing basic blocks
def hook_block(uc, address, size, user_data):
    logger.debug(">>> Tracing basic block at 0x%x, block size = 0x%x" % (address, size))

def hook_code(uc, address, size, user_data):
    logger.debug(">>> Tracing instruction at 0x%x, instruction size = 0x%x" % (address, size))

class emulation_tools():
    def __init__(self,filename):
        self.rf = open(filename, 'rb')
        self.mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        self.memory_map()
        self.memory_init()
        self.elevate_el1()  # Give us EL1 permissions
        self.reg=ARM64Registers(self.mu)
        self.mem=Memory(self.mu)
        #if logger.level==logging.DEBUG:
        self.mu.hook_add(UC_HOOK_BLOCK, hook_block)
        self.mu.hook_add(UC_HOOK_MEM_INVALID, hook_mem_invalid)
        self.mu.hook_add(UC_HOOK_CODE, hook_code, begin=0, end=-1)
        self.mu.hook_add(UC_HOOK_MEM_READ, hook_mem_read)

    def start(self,begin,until,timeout=0,count=0):
        return self.mu.emu_start(begin,until,timeout,count)

    def stop(self):
        return self.mu.emu_stop()

    def get_emulator(self):
        return self.mu

    def pcalc(self,length):
        tmp = length // 1024
        if length % 1024:
            tmp = tmp + 1
        return tmp * 1024

    def elevate_el1(self):
        # If we don't do this, reading from Q0-Q6 will lead to crashes
        fpen = self.mu.reg_read(UC_ARM64_REG_CPACR_EL1)
        fpen |= 0x300000  # FPEN bit
        self.mu.reg_write(UC_ARM64_REG_CPACR_EL1, fpen)
        self.mu.context_save()

    def memory_map(self):
        h = []
        for entry in self.pelf.pentry:
            plen = entry.seg_mem_len
            paddr = entry.phy_addr
            heappush(h, (paddr, plen))

        entries = [heappop(h) for i in range(len(h))]

        oldaddr = 0
        endpos = 0

        for entry in entries:
            if entry[0] > endpos:
                try:
                    self.mu.mem_map(oldaddr, endpos - oldaddr)
                    logging.info(f"Mapped {hex(oldaddr)}:{hex(endpos - oldaddr)}")
                except:
                    logging.error(f"Error on mapping {hex(oldaddr)}:{hex(endpos - oldaddr)}")
                oldaddr = entry[0]
            endpos = self.pcalc(entry[0] + entry[1])
        try:
            self.mu.mem_map(oldaddr, endpos - oldaddr)
            logging.info(f"Mapped {hex(oldaddr)}:{hex(endpos - oldaddr)}")
        except:
            logging.error(f"Error on mapping {hex(oldaddr)}:{hex(endpos - oldaddr)}")

    def memory_init(self):
        for entry in self.pelf.pentry:
            fstart = entry.from_file
            flen = entry.seg_file_len
            pstart = entry.phy_addr
            if flen == 0:
                continue
            self.rf.seek(fstart)
            try:
                self.mu.mem_write(pstart, self.rf.read(flen))
            except:
                logging.error(f"Error on writing elf segment {hex(fstart)} with length {hex(flen)}")

    def replace_function(self,address,callback):
        def hook_code(uc, address, size, user_data):
            logger.debug(">>> Installed hook at 0x%x, instruction size = 0x%x" % (address, size))
            ret = user_data(self.reg)
            uc.reg_write(UC_ARM64_REG_X0, ret)
            uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))
        self.mu.hook_add(UC_HOOK_CODE, hook_code, user_data=callback, begin=address, end=address)

    def monitor_function(self,address,callback):
        def hook_code(uc, address, size, user_data):
            logger.debug(">>> Installed monitor at 0x%x, instruction size = 0x%x" % (address, size))
            user_data(self.reg)
        self.mu.hook_add(UC_HOOK_CODE, hook_code, user_data=callback, begin=address, end=address)