.include "m32def.inc"

;=========================================================
; ATmega32, 8 MHz
; ЛР3, вариант 1
; Секундомер MM.SS
;
; PD2 / INT0  - старт / стоп / возобновление
; PD0         - сохранить текущее значение (только при run)
; PD1         - просмотр сохраненных значений (только при stop)
; PD3 / INT1  - стоп, сброс в 00.00, очистка сохранений
;
; Схема:
;   PORTC    -> сегменты a,b,c,d,e,f,g,dp
;   PORTA.0..3 -> выбор разрядов
;   Индикатор общий анод
;=========================================================

;---------------------------------------------------------
; Константы
;---------------------------------------------------------
.equ T0_PRELOAD = 131        ; 1 ms: 8 MHz / 64 => 125 ticks => 256-125=131
.equ MAX_SAVES  = 8

;---------------------------------------------------------
; Рабочие регистры
;---------------------------------------------------------
.def t0 = r16
.def t1 = r17
.def t2 = r18
.def t3 = r19
.def t4 = r20
.def t5 = r21

;---------------------------------------------------------
; SRAM
;---------------------------------------------------------
.dseg
ms_lo:          .byte 1
ms_hi:          .byte 1

run_flag:       .byte 1      ; 0 - стоп, 1 - идет
disp_mode:      .byte 1      ; 0 - текущее время, 1 - сохраненное
view_index:     .byte 1      ; индекс просматриваемого сохранения
save_count:     .byte 1      ; сколько сохранено
mux_pos:        .byte 1      ; 0..3

btn0_prev:      .byte 1      ; 1 - отпущена, 0 - нажата
btn1_prev:      .byte 1

cur_m10:        .byte 1
cur_m1:         .byte 1
cur_s10:        .byte 1
cur_s1:         .byte 1

disp_m10:       .byte 1
disp_m1:        .byte 1
disp_s10:       .byte 1
disp_s1:        .byte 1

save_buf:       .byte 32     ; 8 значений * 4 цифры

;---------------------------------------------------------
; CODE
;---------------------------------------------------------
.cseg

;---------------------------------------------------------
; Таблица векторов
;---------------------------------------------------------
.org 0x0000
    rjmp RESET
.org 0x0002
    rjmp INT0_ISR
.org 0x0004
    rjmp INT1_ISR
.org 0x0006
    reti
.org 0x0008
    reti
.org 0x000A
    reti
.org 0x000C
    reti
.org 0x000E
    reti
.org 0x0010
    reti
.org 0x0012
    reti
.org 0x0014
    rjmp TIMER0_OVF_ISR

.org 0x0020

;=========================================================
; RESET
;=========================================================
RESET:
    ; Стек
    ldi t0, high(RAMEND)
    out SPH, t0
    ldi t0, low(RAMEND)
    out SPL, t0

    ; PORTC - сегменты, выход
    ldi t0, 0xFF
    out DDRC, t0
    out PORTC, t0            ; погасить сегменты (общий анод)

    ; PORTA0..3 - выбор разрядов, выход
    ldi t0, 0x0F
    out DDRA, t0
    clr t0
    out PORTA, t0

    ; PORTD - кнопки, входы с подтяжкой
    clr t0
    out DDRD, t0
    ldi t0, 0xFF
    out PORTD, t0

    ; Очистка переменных
    clr t0
    sts ms_lo, t0
    sts ms_hi, t0
    sts run_flag, t0
    sts disp_mode, t0
    sts view_index, t0
    sts save_count, t0
    sts mux_pos, t0

    sts cur_m10, t0
    sts cur_m1,  t0
    sts cur_s10, t0
    sts cur_s1,  t0

    sts disp_m10, t0
    sts disp_m1,  t0
    sts disp_s10, t0
    sts disp_s1,  t0

    ldi t0, 1
    sts btn0_prev, t0
    sts btn1_prev, t0

    ; INT0 и INT1 по спадающему фронту
    ldi t0, (1<<ISC01) | (1<<ISC11)
    out MCUCR, t0

    ; Сброс флагов INT0/INT1
    ldi t0, (1<<INTF0) | (1<<INTF1)
    out GIFR, t0

    ; Разрешить INT0, INT1, Timer0 OVF
    ldi t0, (1<<INT0) | (1<<INT1) | (1<<TOIE0)
    out GICR, t0

    ; Timer0: normal mode, prescaler 64
    ldi t0, T0_PRELOAD
    out TCNT0, t0
    ldi t0, (1<<CS01) | (1<<CS00)
    out TCCR0, t0

    sei

MAIN:
    rjmp MAIN

;=========================================================
; INT0 - старт / стоп / возобновление
;=========================================================
INT0_ISR:
    push t0
    push t1
    in t0, SREG
    push t0

    lds t0, run_flag
    ldi t1, 1
    eor t0, t1
    sts run_flag, t0

    ; после переключения режима показываем текущее значение
    clr t0
    sts disp_mode, t0
    rcall COPY_CUR_TO_DISP

    pop t0
    out SREG, t0
    pop t1
    pop t0
    reti

;=========================================================
; INT1 - стоп, сброс, очистка сохранений
;=========================================================
INT1_ISR:
    push t0
    push t1
    push YL
    push YH
    in t0, SREG
    push t0

    clr t0
    sts run_flag, t0
    sts disp_mode, t0
    sts view_index, t0
    sts save_count, t0
    sts ms_lo, t0
    sts ms_hi, t0

    sts cur_m10, t0
    sts cur_m1,  t0
    sts cur_s10, t0
    sts cur_s1,  t0

    sts disp_m10, t0
    sts disp_m1,  t0
    sts disp_s10, t0
    sts disp_s1,  t0

    ; очистка буфера сохранений
    ldi YH, high(save_buf)
    ldi YL, low(save_buf)
    ldi t1, 32
CLR_LOOP:
    st Y+, t0
    dec t1
    brne CLR_LOOP

    pop t0
    out SREG, t0
    pop YH
    pop YL
    pop t1
    pop t0
    reti

;=========================================================
; Timer0 OVF - 1 мс
;=========================================================
TIMER0_OVF_ISR:
    push t0
    push t1
    push t2
    push t3
    push t4
    push t5
    push YL
    push YH
    push ZL
    push ZH
    in t0, SREG
    push t0

    ; Перезагрузка таймера
    ldi t0, T0_PRELOAD
    out TCNT0, t0

    ;-----------------------------------------
    ; 1. Счет миллисекунд
    ;-----------------------------------------
    lds t0, ms_lo
    inc t0
    sts ms_lo, t0
    brne MS_DONE
    lds t0, ms_hi
    inc t0
    sts ms_hi, t0
MS_DONE:

    ; Проверка 1000 мс = 0x03E8
    lds t0, ms_lo
    cpi t0, low(1000)
    brne NO_SECOND
    lds t0, ms_hi
    cpi t0, high(1000)
    brne NO_SECOND

    clr t0
    sts ms_lo, t0
    sts ms_hi, t0

    lds t0, run_flag
    tst t0
    breq NO_SECOND

    rcall INC_STOPWATCH

NO_SECOND:

    ;-----------------------------------------
    ; 2. PD0 - сохранить значение
    ; активный 0, по фронту нажатия
    ;-----------------------------------------
    sbic PIND, PD0
    rjmp BTN0_RELEASED

BTN0_PRESSED:
    lds t0, btn0_prev
    tst t0
    breq CHECK_BTN1
    clr t0
    sts btn0_prev, t0

    ; save только при работе секундомера
    lds t0, run_flag
    tst t0
    breq CHECK_BTN1

    rcall SAVE_CURRENT
    rjmp CHECK_BTN1

BTN0_RELEASED:
    ldi t0, 1
    sts btn0_prev, t0

    ;-----------------------------------------
    ; 3. PD1 - просмотр сохраненных значений
    ; активный 0, по фронту нажатия
    ;-----------------------------------------
CHECK_BTN1:
    sbic PIND, PD1
    rjmp BTN1_RELEASED

BTN1_PRESSED:
    lds t0, btn1_prev
    tst t0
    breq REFRESH_AND_MUX
    clr t0
    sts btn1_prev, t0

    ; просмотр только при остановленном секундомере
    lds t0, run_flag
    tst t0
    brne REFRESH_AND_MUX

    ; если нет сохранений - ничего не делать
    lds t0, save_count
    tst t0
    breq REFRESH_AND_MUX

    ; если еще показывали текущее - открыть первое сохранение
    lds t1, disp_mode
    tst t1
    brne NEXT_SAVE_ITEM

    clr t1
    sts view_index, t1
    ldi t1, 1
    sts disp_mode, t1
    rcall LOAD_VIEW_TO_DISP
    rjmp REFRESH_AND_MUX

NEXT_SAVE_ITEM:
    lds t1, view_index
    inc t1
    lds t2, save_count
    cp t1, t2
    brlo STORE_VIEW_INDEX
    clr t1

STORE_VIEW_INDEX:
    sts view_index, t1
    rcall LOAD_VIEW_TO_DISP
    rjmp REFRESH_AND_MUX

BTN1_RELEASED:
    ldi t0, 1
    sts btn1_prev, t0

    ;-----------------------------------------
    ; 4. если отображается текущее - синхронизировать
    ;-----------------------------------------
REFRESH_AND_MUX:
    lds t0, disp_mode
    tst t0
    brne DO_MUX
    rcall COPY_CUR_TO_DISP

    ;-----------------------------------------
    ; 5. мультиплексирование индикаторов
    ;-----------------------------------------
DO_MUX:
    ; погасить все разряды
    clr t0
    out PORTA, t0

    lds t0, mux_pos
    cpi t0, 0
    breq MUX_0
    cpi t0, 1
    breq MUX_1
    cpi t0, 2
    breq MUX_2
    rjmp MUX_3

MUX_0:
    lds t1, disp_m10
    rcall DIGIT_TO_SEG
    out PORTC, t1
    ldi t1, 0b00000001
    out PORTA, t1
    rjmp MUX_NEXT

MUX_1:
    lds t1, disp_m1
    rcall DIGIT_TO_SEG
    ; включаем точку после минут
    andi t1, 0x7F
    out PORTC, t1
    ldi t1, 0b00000010
    out PORTA, t1
    rjmp MUX_NEXT

MUX_2:
    lds t1, disp_s10
    rcall DIGIT_TO_SEG
    out PORTC, t1
    ldi t1, 0b00000100
    out PORTA, t1
    rjmp MUX_NEXT

MUX_3:
    lds t1, disp_s1
    rcall DIGIT_TO_SEG
    out PORTC, t1
    ldi t1, 0b00001000
    out PORTA, t1

MUX_NEXT:
    lds t0, mux_pos
    inc t0
    cpi t0, 4
    brlo MUX_STORE
    clr t0
MUX_STORE:
    sts mux_pos, t0

    pop t0
    out SREG, t0
    pop ZH
    pop ZL
    pop YH
    pop YL
    pop t5
    pop t4
    pop t3
    pop t2
    pop t1
    pop t0
    reti

;=========================================================
; Подпрограммы
;=========================================================

;---------------------------------------------------------
; COPY_CUR_TO_DISP
;---------------------------------------------------------
COPY_CUR_TO_DISP:
    push t0
    lds t0, cur_m10
    sts disp_m10, t0
    lds t0, cur_m1
    sts disp_m1, t0
    lds t0, cur_s10
    sts disp_s10, t0
    lds t0, cur_s1
    sts disp_s1, t0
    pop t0
    ret

;---------------------------------------------------------
; INC_STOPWATCH
; 00.00 -> 99.59 -> 00.00
;---------------------------------------------------------
INC_STOPWATCH:
    push t0

    lds t0, cur_s1
    inc t0
    cpi t0, 10
    brlo STORE_S1

    clr t0
    sts cur_s1, t0

    lds t0, cur_s10
    inc t0
    cpi t0, 6
    brlo STORE_S10

    clr t0
    sts cur_s10, t0

    lds t0, cur_m1
    inc t0
    cpi t0, 10
    brlo STORE_M1

    clr t0
    sts cur_m1, t0

    lds t0, cur_m10
    inc t0
    cpi t0, 10
    brlo STORE_M10

    clr t0

STORE_M10:
    sts cur_m10, t0
    rjmp INC_END

STORE_M1:
    sts cur_m1, t0
    rjmp INC_END

STORE_S10:
    sts cur_s10, t0
    rjmp INC_END

STORE_S1:
    sts cur_s1, t0

INC_END:
    pop t0
    ret

;---------------------------------------------------------
; SAVE_CURRENT
; сохраняет текущее значение в save_buf
;---------------------------------------------------------
SAVE_CURRENT:
    push t0
    push t1
    push YL
    push YH

    lds t0, save_count
    cpi t0, MAX_SAVES
    brsh SAVE_EXIT

    ldi YH, high(save_buf)
    ldi YL, low(save_buf)

SAVE_OFFSET:
    tst t0
    breq SAVE_DO
    adiw YL, 4
    dec t0
    rjmp SAVE_OFFSET

SAVE_DO:
    lds t1, cur_m10
    st Y+, t1
    lds t1, cur_m1
    st Y+, t1
    lds t1, cur_s10
    st Y+, t1
    lds t1, cur_s1
    st Y+, t1

    lds t0, save_count
    inc t0
    sts save_count, t0

SAVE_EXIT:
    pop YH
    pop YL
    pop t1
    pop t0
    ret

;---------------------------------------------------------
; LOAD_VIEW_TO_DISP
; disp_* = save_buf[view_index]
;---------------------------------------------------------
LOAD_VIEW_TO_DISP:
    push t0
    push YL
    push YH

    ldi YH, high(save_buf)
    ldi YL, low(save_buf)

    lds t0, view_index
LOAD_OFFSET:
    tst t0
    breq LOAD_DO
    adiw YL, 4
    dec t0
    rjmp LOAD_OFFSET

LOAD_DO:
    ld t0, Y+
    sts disp_m10, t0
    ld t0, Y+
    sts disp_m1, t0
    ld t0, Y+
    sts disp_s10, t0
    ld t0, Y+
    sts disp_s1, t0

    pop YH
    pop YL
    pop t0
    ret

;---------------------------------------------------------
; DIGIT_TO_SEG
; вход:  t1 = цифра 0..9
; выход: t1 = код сегментов
;---------------------------------------------------------
DIGIT_TO_SEG:
    push t0
    push ZL
    push ZH

    ldi ZH, high(SEG_TAB*2)
    ldi ZL, low(SEG_TAB*2)
    add ZL, t1
    clr t0
    adc ZH, t0
    lpm t1, Z

    pop ZH
    pop ZL
    pop t0
    ret

;---------------------------------------------------------
; Таблица сегментов для общего анода
; PORTC = abcdefgdp
;---------------------------------------------------------
SEG_TAB:
    .db 0xC0    ; 0
    .db 0xF9    ; 1
    .db 0xA4    ; 2
    .db 0xB0    ; 3
    .db 0x99    ; 4
    .db 0x92    ; 5
    .db 0x82    ; 6
    .db 0xF8    ; 7
    .db 0x80    ; 8
    .db 0x90    ; 9