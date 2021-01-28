#include "common.h"

char SOC_NAME[] = "mt6765";

void (*send_usb_response)(int, int, int) = (void*)0x2D2B;

int (*send_dword)() = (void*)0xBCD3;
// addr, sz
int (*send_data)() = (void*)0xBDA3;
// addr, sz, flags (=0)
int (*recv_data)() = (void*)0xBD15;

uint16_t* sbc = (uint16_t *)0x3A14;
uint16_t* sla = (uint16_t *)0x3A2A;
uint16_t* daa = (uint16_t *)0x3A4E;

#define SLA_PASSED 0x102860;
#define SLA_AUTH_1 0x102A8C;
#define SLA_AUTH_2 0x102A94;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;