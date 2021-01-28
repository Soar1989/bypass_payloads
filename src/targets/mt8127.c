#include "../common/common.h"

char SOC_NAME[] = "mt8127";

void (*send_usb_response)(int, int, int) = (void*)0x62a1;

int (*usbdl_put_dword)() = (void*)0xB1D3;
// addr, sz
int (*usbdl_put_data)() = (void*)0xB29B;
// addr, sz, flags (=0)
int (*usbdl_get_data)() = (void*)0xB215;

volatile char *SLA_PASSED=(volatile char *)0x1027E4;
volatile uint32_t *SLA_PASSED1=(volatile uint32_t *)0x102824;
volatile uint32_t *SLA_CHECK=(volatile uint32_t *)0x1028A4;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;
