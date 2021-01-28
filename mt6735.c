#include "common.h"

char SOC_NAME[] = "mt6735";

void (*send_usb_response)(int, int, int) = (void*)0x4293;

int (*send_dword)() = (void*)0x9513;
// addr, sz
int (*send_data)() = (void*)0x95DB;
// addr, sz, flags (=0)
int (*recv_data)() = (void*)0x9555;

uint16_t* sbc = (uint16_t *)0x4F52;
uint16_t* sla = (uint16_t *)0x4F6A;
uint16_t* daa = (uint16_t *)0x4F8E;

#define SLA_PASSED 0x102794;
#define SLA_AUTH_1 0x102714;
#define SLA_AUTH_2 0x1026D4;

volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11002014;
volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11002000;