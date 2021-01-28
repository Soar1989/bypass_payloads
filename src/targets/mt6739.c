#include "../common/common.h"

char SOC_NAME[] = "mt6739";

void (*send_usb_response)(int, int, int) = (void*)0x508B;

int (*usbdl_put_dword)() = (void*)0xDE2F;
// addr, sz
int (*usbdl_put_data)() = (void*)0xDEFF;
// addr, sz, flags (=0)
int (*usbdl_get_data)() = (void*)0xDE71;

volatile char *SLA_PASSED=(volatile char *)0x102864;
volatile uint32_t *SLA_PASSED1=(volatile uint32_t *)0x102A8C;
volatile uint32_t *SLA_CHECK=(volatile uint32_t *)0x102A94;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;
