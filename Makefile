
CC := arm-none-eabi-gcc
AS := arm-none-eabi-as
LD := arm-none-eabi-gcc
OBJCOPY := arm-none-eabi-objcopy

VPATH := src/targets src/common src/generic

SOCS := mt6580 mt6735 mt6737 mt6739 mt6750 mt6757 mt6761 mt6765 mt6768 mt6771 mt6785 mt6873 mt8127 mt8163 mt8173 mt8695 generic_dump generic_reboot generic_uart_dump generic_patcher
PAYLOADS := $(SOCS:%=payloads/%_payload.bin)

CFLAGS := -std=gnu99 -Os -mthumb -mcpu=cortex-a9 -fno-builtin-printf -fno-strict-aliasing -fno-builtin-memcpy -fPIE -mno-unaligned-access -Wall -Wextra
LDFLAGS := -nodefaultlibs -nostdlib -lgcc

COMMON_OBJ = payloads/common.o payloads/start.o

all: $(PAYLOADS)

payloads/%_payload.bin: payloads/%.elf
	$(OBJCOPY) -O binary $^ $@


payloads/%.elf: payloads/%.o payloads/start.o generic.ld
	$(LD) -o $@ payloads/$*.o payloads/start.o $(LDFLAGS) -T src/generic/generic.ld

payloads/generic_%.o: generic_%.c
	mkdir -p $(@D)
	$(CC) -c -o $@ $< $(CFLAGS)

payloads/%.o: common.c %.h
	mkdir -p $(@D)
	$(CC) -c -o $@ src/common/common.c -D DEVICE_HEADER=../targets/$*.h $(CFLAGS)

payloads/%.o: %.S
	mkdir -p $(@D)
	$(AS) -o $@ $<

clean:
	-rm -rf payloads