#include "../common/common.h"

char SOC_NAME[] = "mt8163";

void (*send_usb_response)(int, int, int) = (void*)0x6d6f;

int (*usbdl_put_dword)() = (void*)0xC047;
// addr, sz
int (*usbdl_put_data)() = (void*)0xC10F;
// addr, sz, flags (=0)
int (*usbdl_get_data)() = (void*)0xC089;

volatile char *SLA_PASSED=(volatile char *)0x1027DC;
volatile uint32_t *SLA_PASSED1=(volatile uint32_t *)0x10281C;
volatile uint32_t *SLA_CHECK=(volatile uint32_t *)0x10289C;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;
