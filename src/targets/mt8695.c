#include "../common/common.h"

char SOC_NAME[] = "mt8695";

void (*send_usb_response)(int, int, int) = (void*)0x55bb;

int (*usbdl_put_dword)() = (void*)0xBE09;
// addr, sz
int (*usbdl_put_data)() = (void*)0xBED1;
// addr, sz, flags (=0)
int (*usbdl_get_data)() = (void*)0xBE4B;

volatile char *SLA_PASSED=(volatile char *)0x102FBC; 
volatile uint32_t *SLA_PASSED1= (volatile uint32_t *)0x102FBC + 0x40;
volatile uint32_t *SLA_CHECK=(volatile uint32_t *)0x10307C;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11003014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11003000;
