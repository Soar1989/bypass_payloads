#include "../common/common.h"

char SOC_NAME[] = "mt6580";

void (*send_usb_response)(int, int, int) = (void*)0x62E5;

int (*usbdl_put_dword)() = (void*)0xB527;
// addr, sz
int (*usbdl_put_data)() = (void*)0xB5EF;
// addr, sz, flags (=0)
int (*usbdl_get_data)() = (void*)0xB569;

volatile char *SLA_PASSED=(volatile char *)0x1026D8;
volatile uint32_t *SLA_PASSED1= (volatile uint32_t *)0x1026D8 + 0x40;
volatile uint32_t *SLA_CHECK=(volatile uint32_t *)0x102798;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11005014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11005000;