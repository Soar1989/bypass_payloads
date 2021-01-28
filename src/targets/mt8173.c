#include "../common/common.h"

char SOC_NAME[] = "mt8173";

void (*send_usb_response)(int, int, int) = (void*)0x4c5f;

int (*usbdl_put_dword)() = (void*)0x9FFF;
// addr, sz
int (*usbdl_put_data)() = (void*)0xA0C7;
// addr, sz, flags (=0)
int (*usbdl_get_data)() = (void*)0xA041;

volatile char *SLA_PASSED=(volatile char *)0x1226E8;
volatile uint32_t *SLA_PASSED1= (volatile uint32_t *)0x1226E8 + 0x40;
volatile uint32_t *SLA_CHECK=(volatile uint32_t *)0x1227A8;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;
