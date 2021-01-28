#include "common.h"

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

int main() {
    print("Entered ");
    print(SOC_NAME);
    print(" brom patcher\n");

    print("Copyright k4y0z/bkerler 2021\n");

    //This is so we don't get a USB-Timeout
    print("Send USB response\n");
    send_usb_response(1,0,1);
    
    print("Sending ACK\n");
    usbdl_put_dword(0xA1A2A3A4);

    *SLA_PASSED = 1;
    *SLA_PASSED1 = 1;
    *SLA_CHECK = -1;

    //invalidate icache
    asm volatile ("mcr p15, 0, %0, c7, c5, 0" : : "r" (0));

    const char sequence[] = {0xA0, 0x0A, 0x50, 0x05};
    unsigned int index = 0;
    unsigned char hs = 0;

    print("Waiting for handshake...\n");
    do {
        while ( ((*uart_reg0) & 1) ) {}
        while ( 1 ) {
            usbdl_get_data(&hs, 1);
            if(sequence[index] == hs) break;
            index = 0;
            print("\nHandshake failed!\n");
        }
        hs = ~hs;
        usbdl_put_data(&hs, 1);
        index += 1;
        print(".");
    } while(index != 4);

    print("\nHandshake completed!\n");
}