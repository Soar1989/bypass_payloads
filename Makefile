
CC := arm-none-eabi-gcc
AS := arm-none-eabi-as
LD := arm-none-eabi-gcc
OBJCOPY := arm-none-eabi-objcopy
VPATH := src/targets src/common src/generic
SOCS := mt6580 mt6735 mt6737 mt6739 mt6750 mt6761 mt6765 mt6771 mt8127 mt8163 mt8173 mt8695 generic_dump generic_reboot generic_uart_dump
PAYLOADS := $(SOCS:%=payloads/%_payload.bin)

CFLAGS := -std=gnu99 -Os -mthumb -mcpu=cortex-a9 -fno-builtin-printf -fno-strict-aliasing -fno-builtin-memcpy -fPIE -mno-unaligned-access -Wall -Wextra
LDFLAGS := -nodefaultlibs -nostdlib -lgcc

COMMON_OBJ = payloads/common.o payloads/start.o

all: $(PAYLOADS)

payloads/%_payload.bin: payloads/%.elf
	$(OBJCOPY) -O binary $^ $@

payloads/generic_%.elf: payloads/generic_%.o payloads/generic.o src/generic/generic.ld
	$(LD) -o $@ payloads/generic_$*.o payloads/generic.o $(LDFLAGS) -T src/generic/generic.ld

payloads/%.elf: payloads/%.o $(COMMON_OBJ) %.ld
	$(LD) -o $@ payloads/$*.o $(COMMON_OBJ) $(LDFLAGS) -T src/targets/$*.ld

payloads/%.o: %.c
	mkdir -p $(@D)
	$(CC) -c -o $@ $< $(CFLAGS)

payloads/%.o: %.S
	mkdir -p $(@D)
	$(AS) -o $@ $<

clean:
	-rm -rf payloads