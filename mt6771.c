#include "common.h"

char SOC_NAME[] = "mt6771";

void (*send_usb_response)(int, int, int) = (void*)0x4DAF;

int (*send_dword)() = (void*)0xDDCF;
// addr, sz
int (*send_data)() = (void*)0xDE9F;
// addr, sz, flags (=0)
int (*recv_data)() = (void*)0xDE11;

uint16_t* sbc = (uint16_t *)0x5B2B;
uint16_t* sla = (uint16_t *)0x5B3E;
uint16_t* daa = (uint16_t *)0x5B62;

#define SLA_PASSED 0x10286C;
#define SLA_AUTH_1 0x102ACC;
#define SLA_AUTH_2 0x102AD4;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;