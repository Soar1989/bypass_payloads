#include "../common/common.h"

char SOC_NAME[] = "mt6768";

void (*send_usb_response)(int, int, int) = (void*)0x2C2F;

int (*send_dword)() = (void*)0xC0A3;
// addr, sz
int (*send_data)() = (void*)0xC173;
// addr, sz, flags (=0)
int (*recv_data)() = (void*)0xC0E5;

volatile char *SLA_PASSED=(volatile char *)0x102860;
volatile uint32_t *SLA_AUTH_1=(volatile uint32_t *)0x102A8C;
volatile uint32_t *SLA_AUTH_2=(volatile uint32_t *)0x102A94;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;