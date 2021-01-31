#!/usr/bin/env python3
#(c) B.Kerler 2021 MIT License
import sys
from binascii import unhexlify
from struct import unpack

def find_binary(data, strf, pos=0):
    if isinstance(strf,str):
        strf=unhexlify(strf)
    t = strf.split(b".")
    pre = 0
    offsets = []
    while pre != -1:
        pre = data[pos:].find(t[0], pre)
        if pre==-1:
            break
        offsets.append(pre)
        pre += 1

    for offset in offsets:
        error = 0
        rt = pos+offset + len(t[0])
        for i in range(1, len(t)):
            if t[i] == b'':
                rt += 1
                continue
            rt += 1
            rdat=data[rt:]
            prep = rdat.find(t[i])
            if prep != 0:
                error = 1
                break
            rt += len(t[i])
        if error == 0:
            return pos+offset

    return None

def main():
    if len(sys.argv)<2:
        print("Usage: ./brom_to_offs.py brom.bin")
        sys.exit(0)
    with open(sys.argv[1],"rb") as rf:
        data=rf.read()
        pos = find_binary(data, b"\x30\xB5\x00\x23.\x4C\x08\x28\x0F\xD0", 0)
        if pos==None:
            pos = find_binary(data, "10B500244FF08953032806D0", 0)
            if pos == None:
                pos = find_binary(data, "10B5724B0024032806D00228", 0)
        if pos != None:
            pos += 1
            print("*send_usb_response:\t0x%08X" % pos)
        else:
            print("*send_usb_response=None")

        pos=find_binary(data,"2DE9F84F80468A46",0)
        if pos!=None:
            pos += 1
            #print("*send_word:\t\t\t0x%08X" % pos)
            pos = find_binary(data, "2DE9F84F80468A46", pos+1)
            if pos != None:
                pos += 1
                #print("*usbdl_put_dword:\t\t0x%08X" % pos)
        else:
            print("*usbdl_put_dword=None")
        """
        pos = find_binary(data,b"\x2D\xE9\xF8\x43.\x48.\x68.\x25.\x24", 0)
        if pos!=None:
            pos+=1
            #print("*recv_word:\t\t\t0x%08X" % pos)
            pos = find_binary(data, b"\x2D\xE9\xF8\x43.\x48.\x68.\x25.\x24", pos)
            if pos != None:
                pos += 1
                print("*recv_dword:\t\t0x%08X" % pos)
            else:
                print("*recv_dword=None")
        else:
            print("*recv_word=None")
            print("*recv_dword=None")
        """
        pos = find_binary(data, "10B5064AD468", 0)
        if pos != None:
            pos += 1
            print("*usbdl_put_data:\t\t\t0x%08X" % pos)
        pos = find_binary(data, b"\x10\xB5.\xF0...\x46", 0)
        if pos == None:
            pos = find_binary(data, b"\x10\xB5.\xF0...\x49", 0)
        else:
            pos2 = find_binary(data, "46FFF7", pos + 8)
            if pos2 != None:
                if pos2 - pos < 0x20:
                    pos = pos
                else:
                    pos = pos2 - 1
        posr=-1
        startpos=0
        while posr!=None:
            posr=find_binary(data, "2DE9F047", startpos)
            if posr==None:
                break
            if data[posr+7]==0x46 and data[posr+8]==0x92:
                break
            startpos=posr+2
        """
        posr = find_binary(data, "2DE9F04780460F469246", 0)
        if posr == None:
            posr = find_binary(data, "2DE9F047074688469246", 0)
        """
        if posr != None:
            posr += 1
            print("*usbdl_get_data:\t\t\t0x%08X" % posr)
        else:
            print("*usbdl_get_data=None")

        pattern=b"\xB5.\xF0"
        if pos != None:
            sbcpos=pos
            print("sbc:\t\t\t\t0x%08X" % pos)
            pos = find_binary(data, pattern, pos+8)
            if pos != None:
                pos-=1
                print("sla:\t\t\t\t0x%08X" % pos)
                if pos != None:
                    pos = find_binary(data, pattern, pos+2)
                    if pos != None:
                        pos-=1
                        print("daa:\t\t\t\t0x%08X" % pos)
        else:
            print("*send_data=None")

        pos = find_binary(data, "70B50646A648", 0)
        if pos != None:
            pos += 1
            print("*func_acm:\t\t\t0x%08X" % pos)
        pos = find_binary(data, "0F4941F6", 0)
        if pos==None:
            pos = find_binary(data, "124941F6",0)
        if pos != None:
            pos += 1
            print("*func_wdt:\t\t\t0x%08X" % pos)
        pos = find_binary(data, "F8B50024", 0)
        if pos!=None:
            pos += 1
            print("*func_usb_buffer:\t\t0x%08X" % pos)
        pos = find_binary(data, "FFF7F4FF", 0)
        if pos==None:
            pos = find_binary(data, b"\x10\xB5..\xF4.\x00\x21", 0)
        if pos!=None:
            pos += 1
            print("*cmd_handler:\t\t\t0x%08X" % pos)
        else:
            print("*cmd_handler=None")

        pos = find_binary(data, b"\xA1..\xD0\x21..\xD0\x00\x22", 0)
        if pos != None:
            pos-=1
            print("vuln_ctrl_handler:\t Around offset 0x%08X" % pos)
        else:
            print("*vuln_ctrl_handler=None")

        pos = find_binary(data,"10B5114A")
        if pos != None:
            print("uart_info:\t Around offset 0x%08X" % pos)

        pos = find_binary(data,"315F454E930F0E00")
        if pos != None:
            pos+=8
            uart_addr=unpack("<I",data[pos:pos+4])[0]
            print("uart_addr0:\t 0x%08X" % (uart_addr+0x14))
            print("uart_addr1:\t 0x%08X" % uart_addr)

        pos = find_binary(data,"33332F4005000022")
        if pos != None:
            pos-=4
            wd=unpack("<I",data[pos:pos+4])[0]
            print("wd:\t 0x%08X" % wd)

if __name__=="__main__":
    main()