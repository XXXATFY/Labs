.def TMP        = R16
.def PIN0       = R28   ; Правильная цифра 1
.def PIN1       = R18   ; Правильная цифра 2
.def PIN2       = R19   ; Правильная цифра 3
.def PIN3       = R20   ; Правильная цифра 4
.def SPIN0      = R21   ; Вводимая цифра 1
.def SPIN1      = R22   ; Вводимая цифра 2
.def SPIN2      = R23   ; Вводимая цифра 3
.def SPIN3      = R24   ; Вводимая цифра 4
.def WRONG      = R25   ; Количество ошибочных попыток ввода PIN-кода
.def DIGIT      = R26   ; Текущий редактируемый разряд
.def SHOW       = R27   ; Текущий отображаемый разряд
.def DEL2SEC    = R17   ; Счётчик задержки удержания кнопки, шаг 10 мс
.def DEL250MS   = R29   ; Счётчик задержки автоповтора, шаг 10 мс
.def INPDLOOP   = R30   ; Флаг состояния удержания кнопки / режима ошибки
.def BLINK      = R31   ; Счётчик мигания текущего разряда, шаг 5 мс

.org $0000
    RJMP reset
.org INT0addr
    RJMP EXT_INT0
.org INT1addr
    RJMP EXT_INT1
.org OC2addr
    RJMP TIMER2_COMP_ISR
.org OC0addr
    RJMP TIMER0_COMP_ISR

; Обработка удержания кнопок PD0 и PD1
; После первого нажатия ждём 2 секунды.
; Затем при удержании выполняется автоповтор каждые 250 мс.
calc_delay:
    IN   TMP, PIND
    ANDI TMP, 0x03

    CPI  TMP, 0x00
    BREQ reset_delay
    CPI  TMP, 0x03
    BREQ reset_delay

    ; Счётчик задержки перед автоповтором
    ; Timer2 вызывает это место каждые 10 мс
    ; 200 * 10 мс = 2 секунды
    INC  DEL2SEC
    CPI  DEL2SEC, 200
    BREQ pdsdelay

    ; Если режим автоповтора уже включён, продолжаем считать 250 мс
    CPI  INPDLOOP, 0x01
    BRGE pdsdelay

    RET

pdsdelay:
    ; Включаем режим удержания кнопки
    LDI  INPDLOOP, 0x01

    ; 25 * 10 мс = 250 мс
    INC  DEL250MS
    CPI  DEL250MS, 25
    BREQ pdsloop
    RET

pdsloop:
    ; Прошло 250 мс - выполняем изменение цифры
    LDI  DEL250MS, 0x00
    CPI  TMP, 0x01
    BREQ increase_digit
    BRNE decrease_digit

reset_delay:
    ; Сброс состояния удержания после отпускания кнопки
    LDI  INPDLOOP, 0x00
    LDI  DEL250MS, 0x00
    LDI  DEL2SEC, 0x00

return:
    RET


; Обработка короткого нажатия кнопок PD0 и PD1
; PD0 - увеличение текущей цифры
; PD1 - уменьшение текущей цифры
check_buttons:
    ; Если DEL2SEC не равен нулю, значит кнопка уже была обработана
    CPI  DEL2SEC, 0x00
    BRNE return

    IN   TMP, PIND
    ANDI TMP, 0x03

    CPI  TMP, 0x01
    BREQ check_inc
    CPI  TMP, 0x02
    BREQ check_dec
    RET

check_inc:
    CALL increase_digit
    LDI  DEL2SEC, 0x01
    LDI  DEL250MS, 0x00
    LDI  INPDLOOP, 0x00
    RET

check_dec:
    CALL decrease_digit
    LDI  DEL2SEC, 0x01
    LDI  DEL250MS, 0x00
    LDI  INPDLOOP, 0x00
    RET


; Увеличение текущей редактируемой цифры
increase_digit:
    CPI DIGIT, 0x01
    BREQ increase_spin0
    CPI DIGIT, 0x02
    BREQ increase_spin1
    CPI DIGIT, 0x04
    BREQ increase_spin2
    CPI DIGIT, 0x08
    BREQ increase_spin3

increase_spin0:
    CPI SPIN0, 0x09
    BRNE increase_spin0_loop
    LDI SPIN0, 0x00
    RET
increase_spin0_loop:
    INC SPIN0
    RET

increase_spin1:
    CPI SPIN1, 0x09
    BRNE increase_spin1_loop
    LDI SPIN1, 0x00
    RET
increase_spin1_loop:
    INC SPIN1
    RET

increase_spin2:
    CPI SPIN2, 0x09
    BRNE increase_spin2_loop
    LDI SPIN2, 0x00
    RET
increase_spin2_loop:
    INC SPIN2
    RET

increase_spin3:
    CPI SPIN3, 0x09
    BRNE increase_spin3_loop
    LDI SPIN3, 0x00
    RET
increase_spin3_loop:
    INC SPIN3
    RET


; Уменьшение текущей редактируемой цифры
decrease_digit:
    CPI DIGIT, 0x01
    BREQ decrease_spin0
    CPI DIGIT, 0x02
    BREQ decrease_spin1
    CPI DIGIT, 0x04
    BREQ decrease_spin2
    CPI DIGIT, 0x08
    BREQ decrease_spin3

decrease_spin0:
    CPI SPIN0, 0x00
    BRNE decrease_spin0_loop
    LDI SPIN0, 0x09
    RET
decrease_spin0_loop:
    DEC SPIN0
    RET

decrease_spin1:
    CPI SPIN1, 0x00
    BRNE decrease_spin1_loop
    LDI SPIN1, 0x09
    RET
decrease_spin1_loop:
    DEC SPIN1
    RET

decrease_spin2:
    CPI SPIN2, 0x00
    BRNE decrease_spin2_loop
    LDI SPIN2, 0x09
    RET
decrease_spin2_loop:
    DEC SPIN2
    RET

decrease_spin3:
    CPI SPIN3, 0x00
    BRNE decrease_spin3_loop
    LDI SPIN3, 0x09
    RET
decrease_spin3_loop:
    DEC SPIN3
    RET


; Чтение PIN-кода из EEPROM
; PIN хранится по адресам 0x00, 0x01, 0x02, 0x03
eeprom_read:
    ; Чтение PIN0
    LDI  TMP, 0x00
    OUT  EEARH, TMP
    LDI  TMP, 0x00
    OUT  EEARL, TMP
    SBI  EECR, EERE
    IN   PIN0, EEDR

    ; Чтение PIN1
    LDI  TMP, 0x00
    OUT  EEARH, TMP
    LDI  TMP, 0x01
    OUT  EEARL, TMP
    SBI  EECR, EERE
    IN   PIN1, EEDR

    ; Чтение PIN2
    LDI  TMP, 0x00
    OUT  EEARH, TMP
    LDI  TMP, 0x02
    OUT  EEARL, TMP
    SBI  EECR, EERE
    IN   PIN2, EEDR

    ; Чтение PIN3
    LDI  TMP, 0x00
    OUT  EEARH, TMP
    LDI  TMP, 0x03
    OUT  EEARL, TMP
    SBI  EECR, EERE
    IN   PIN3, EEDR

    RET


; Инициализация микроконтроллера
reset:
    ; Инициализация стека
    LDI  TMP, HIGH(RAMEND)
    OUT  SPH, TMP
    LDI  TMP, LOW(RAMEND)
    OUT  SPL, TMP

    ; PORTA - управление разрядами семисегментного индикатора
    ; PA0..PA3 - выбор разряда
    ; PA6 - индикация ошибки
    ; PA7 - индикация правильного PIN-кода
    SER  TMP
    OUT  DDRA, TMP
    CLR  TMP
    OUT  PORTA, TMP

    ; PORTC — сегменты семисегментного индикатора
    SER  TMP
    OUT  DDRC, TMP
    OUT  PORTC, TMP

    ; PORTD:
    ; PD0 - кнопка увеличения цифры
    ; PD1 - кнопка уменьшения цифры
    ; PD2 - INT0, переход к предыдущему разряду
    ; PD3 - INT1, переход к следующему разряду / проверка PIN-кода
    ; PD4..PD7 — выходы
    LDI  TMP, 0xF0
    OUT  DDRD, TMP
    CLR  TMP
    OUT  PORTD, TMP

    ; Начальные значения переменных
    LDI  WRONG, 0x00
    LDI  DIGIT, 0x01
    LDI  DEL2SEC, 0x00
    LDI  DEL250MS, 0x00
    LDI  SPIN0, 0x00
    LDI  SPIN1, 0x00
    LDI  SPIN2, 0x00
    LDI  SPIN3, 0x00
    LDI  PIN0, 0x00
    LDI  PIN1, 0x00
    LDI  PIN2, 0x00
    LDI  PIN3, 0x00
    LDI  BLINK, 0x00

    ; Чтение правильного PIN-кода из EEPROM
    ;CALL eeprom_read

    ; Настройка внешних прерываний INT0 и INT1
    ; INT0 и INT1 срабатывают по переднему фронту (0 -> 1)
    LDI  R16, 0x0F
    OUT  MCUCR, R16

    ; Разрешение INT0 и INT1
    ; GICR = 0xC0: включены INT1 и INT0
    LDI  R16, 0xC0
    OUT  GICR, R16
    OUT  GIFR, R16

    ; Timer0 — мигание текущего разряда
    ; Режим CTC, предделитель 256
    ; OCR0 = 155
    ; Период: 156 * 256 / 8 МГц = 5 мс
    LDI  TMP, 0x0C
    OUT  TCCR0, TMP
    LDI  TMP, 155
    OUT  OCR0, TMP

    ; Timer2 — опрос кнопок и временные задержки
    ; Режим CTC, предделитель 1024
    ; OCR2 = 77
    ; Период: 78 * 1024 / 8 МГц = 10 мс
    LDI  TMP, 0x0F
    OUT  TCCR2, TMP
    LDI  TMP, 77
    OUT  OCR2, TMP

    ; Разрешение прерываний по совпадению Timer0 и Timer2
    ; TIMSK = 0x82: OCIE2 = 1, OCIE0 = 1
    LDI  TMP, 0x82
    OUT  TIMSK, TMP

    ; Глобальное разрешение прерываний
    SEI


; Основной цикл программы
; Поочерёдно выводит четыре цифры PIN-кода на индикатор
loop:
    CPI INPDLOOP, 0x02
    BREQ wrong_wait_loop

    CPI WRONG, 0xFF
    BREQ correct_loop

    LDI SHOW, 0x01
    MOV TMP, SPIN0
    CALL show_digit
    
    LSL SHOW
    MOV TMP, SPIN1
    CALL show_digit
    
    LSL SHOW
    MOV TMP, SPIN2
    CALL show_digit

    LSL SHOW
    MOV TMP, SPIN3
    CALL show_digit

    RJMP loop


; Режим правильного ввода PIN-кода
; На индикатор выводится 9999, включается PA7
correct_loop:
    LDI  SPIN0, 0x09
    LDI  SPIN1, 0x09
    LDI  SPIN2, 0x09
    LDI  SPIN3, 0x09
    LDI  TMP, 0x80
    OUT  PORTA, TMP
    RJMP loop


; Сравнение введённого PIN-кода с правильным PIN-кодом
compare_pins:
    CP  SPIN0, PIN0
    BRNE wrong_pin
    CP  SPIN1, PIN1
    BRNE wrong_pin
    CP  SPIN2, PIN2
    BRNE wrong_pin
    CP  SPIN3, PIN3
    BRNE wrong_pin

    LDI TMP, 0xFF
    MOV WRONG, TMP
    RET


; Обработка неверного PIN-кода
wrong_pin:
    INC WRONG
    CPI WRONG, 0x03
    BREQ lock

    LDI TMP, 0x40
    OUT PORTA, TMP

    LDI INPDLOOP, 0x02
    LDI DEL2SEC, 0x00
    LDI DEL250MS, 0x00
    RET


; Ожидание после неверного PIN-кода
wrong_wait_loop:
    LDI TMP, 0x40
    OUT PORTA, TMP

    CPI WRONG, 0xFF
    BREQ correct_loop

    RJMP loop


; Блокировка после трёх неверных попыток
lock:
    LDI TMP, 0xC0
    OUT PORTA, TMP
l:
    RJMP l


; Вывод одной цифры на семисегментный индикатор
; Если отображаемый разряд совпадает с DIGIT, он мигает с частотой 4 Гц
show_digit:
    CP   SHOW, DIGIT
    BRNE show_num

    ; Фаза выключения мигающего разряда
    ; BLINK = 0..24 - разряд выключен
    ; BLINK = 25..49 - разряд включен
    CPI  BLINK, 25
    BRGE show_num

    CLR  TMP
    OUT  PORTA, TMP
    RET

show_num:
    CALL code_to_portc
    MOV  TMP, SHOW
    OUT  PORTA, TMP
    NOP
    NOP
    NOP
    RET


; Преобразование цифры 0..9 в код для PORTC
code_to_portc:
    CPI TMP, 0x00
    BREQ code0
    CPI TMP, 0x01
    BREQ code1
    CPI TMP, 0x02
    BREQ code2
    CPI TMP, 0x03
    BREQ code3
    CPI TMP, 0x04
    BREQ code4
    CPI TMP, 0x05
    BREQ code5
    CPI TMP, 0x06
    BREQ code6
    CPI TMP, 0x07
    BREQ code7
    CPI TMP, 0x08
    BREQ code8
    CPI TMP, 0x09
    BREQ code9

code0:
    LDI TMP, 0xC0
    OUT PORTC, TMP
    RET
code1:
    LDI TMP, 0xF9
    OUT PORTC, TMP
    RET
code2:
    LDI TMP, 0xA4
    OUT PORTC, TMP
    RET
code3:
    LDI TMP, 0xB0
    OUT PORTC, TMP
    RET
code4:
    LDI TMP, 0x99
    OUT PORTC, TMP
    RET
code5:
    LDI TMP, 0x92
    OUT PORTC, TMP
    RET
code6:
    LDI TMP, 0x82
    OUT PORTC, TMP
    RET
code7:
    LDI TMP, 0xF8
    OUT PORTC, TMP
    RET
code8:
    LDI TMP, 0x80
    OUT PORTC, TMP
    RET
code9:
    LDI TMP, 0x90
    OUT PORTC, TMP
    RET


; Прерывание INT0
; Переход к предыдущему разряду PIN-кода
EXT_INT0:
    PUSH TMP
    IN   TMP, SREG
    PUSH TMP

    CPI  DIGIT, 0x01
    BREQ int0_return

    LSR  DIGIT

int0_return:
    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI


; Прерывание Timer0
; Timer0 срабатывает каждые 5 мс
TIMER0_COMP_ISR:
    PUSH TMP
    IN   TMP, SREG
    PUSH TMP
    MOV  TMP, SHOW
    PUSH TMP

    CPI  INPDLOOP, 0x02
    BREQ timer0_exit
    CPI  WRONG, 0xFF
    BREQ timer0_exit

    ; 25 * 5 мс = 125 мс
    ; 50 * 5 мс = 250 мс, то есть частота мигания 4 Гц
    INC  BLINK
    CPI  BLINK, 50
    BRLO timer0_exit
    LDI  BLINK, 0x00

timer0_exit:
    POP  TMP
    MOV  SHOW, TMP
    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI


; Прерывание Timer2
; Timer2 срабатывает каждые 10 мс
TIMER2_COMP_ISR:
    PUSH TMP
    IN   TMP, SREG
    PUSH TMP
    MOV  TMP, SHOW
    PUSH TMP

    CPI  INPDLOOP, 0x02
    BREQ error_mode_timer2

    CPI  WRONG, 0xFF
    BREQ error_mode_timer2

    CPI  INPDLOOP, 0x00
    BRNE skip_check
    CALL check_buttons

skip_check:
    CALL calc_delay
    RJMP timer2_exit

error_mode_timer2:
    ; Timer2 срабатывает каждые 10 мс
    ; 100 * 10 мс = 1 секунда
    INC  DEL2SEC
    CPI  DEL2SEC, 100
    BRNE timer2_exit

    ; Прошла 1 секунда
    LDI  DEL2SEC, 0x00
    INC  DEL250MS

    ; 20 * 1 секунда = 20 секунд ожидания после ошибки
    CPI  DEL250MS, 20
    BRNE timer2_exit

    ; Ожидание закончено: сброс введённого PIN-кода и возврат к вводу
    CLR  TMP
    OUT  PORTA, TMP

    LDI  DIGIT, 0x01
    LDI  SHOW, 0x01

    LDI  SPIN0, 0x00
    LDI  SPIN1, 0x00
    LDI  SPIN2, 0x00
    LDI  SPIN3, 0x00

    LDI  DEL2SEC, 0x00
    LDI  DEL250MS, 0x00
    LDI  INPDLOOP, 0x00

timer2_exit:
    POP  TMP
    MOV  SHOW, TMP
    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI


; Прерывание INT1
; Переход к следующему разряду.
; Если выбран последний разряд, выполняется проверка PIN-кода.
EXT_INT1:
    PUSH TMP
    IN   TMP, SREG
    PUSH TMP

    CPI  DIGIT, 0x08
    BREQ call_compare_pins

    LSL  DIGIT

int1_return:
    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI

call_compare_pins:
    CALL compare_pins
    RJMP int1_return