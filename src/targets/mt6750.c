#include "../common/common.h"

char SOC_NAME[] = "mt6750";

void (*send_usb_response)(int, int, int) = (void*)0x449f;

int (*usbdl_put_dword)() = (void*)0x9987;
// addr, sz
int (*usbdl_put_data)() = (void*)0x9A4F;
// addr, sz, flags (=0)
int (*usbdl_get_data)() = (void*)0x99C9;

volatile char *SLA_PASSED=(volatile char *)0x1026DC;
volatile uint32_t *SLA_PASSED1=(volatile uint32_t *)0x10271C;
volatile uint32_t *SLA_CHECK=(volatile uint32_t *)0x1027A4;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;