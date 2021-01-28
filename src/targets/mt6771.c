#include "../common/common.h"

char SOC_NAME[] = "mt6771";

void (*send_usb_response)(int, int, int) = (void*)0x4DAF;

int (*usbdl_put_dword)() = (void*)0xDDCF;
// addr, sz
int (*usbdl_put_data)() = (void*)0xDE9F;
// addr, sz, flags (=0)
int (*usbdl_get_data)() = (void*)0xDE11;

volatile char *SLA_PASSED=(volatile char *)0x10286C;
volatile uint32_t *SLA_PASSED1=(volatile uint32_t *)0x102ACC;
volatile uint32_t *SLA_CHECK=(volatile uint32_t *)0x102AD4;


volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;