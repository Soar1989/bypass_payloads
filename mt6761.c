#include "common.h"

char SOC_NAME[] = "mt6761";

void (*send_usb_response)(int, int, int) = (void*)0x2CDF;

int (*send_dword)() = (void*)0xBB9F;
// addr, sz
int (*send_data)() = (void*)0xBC6F;
// addr, sz, flags (=0)
int (*recv_data)() = (void*)0xBBE1;

uint16_t* sbc = (uint16_t *)0x39C8;
uint16_t* sla = (uint16_t *)0x39DE;
uint16_t* daa = (uint16_t *)0x3A02;

#define SLA_PASSED 0x102860;
#define SLA_AUTH_1 0x102A8C;
#define SLA_AUTH_2 0x102A94;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;