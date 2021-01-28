#ifndef _COMMON_H_
#define _COMMON_H_

#include <inttypes.h>

extern char SOC_NAME[];

void (*send_usb_response)(int, int, int);

int (*usbdl_put_dword)();
int (*recv_dword)();
// addr, sz
int (*usbdl_put_data)();
// addr, sz, flags (=0)
int (*usbdl_get_data)();

extern volatile uint32_t *uart_reg0;
extern volatile uint32_t *uart_reg1;
extern volatile char *SLA_PASSED;
extern volatile uint32_t *SLA_PASSED1;
extern volatile uint32_t *SLA_CHECK;

void low_uart_put(int ch);

void _putchar(char character);

#endif
