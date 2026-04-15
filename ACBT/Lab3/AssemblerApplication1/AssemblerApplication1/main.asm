.def TMP        = R16 
.def PIN0       = R28	; Правильная цифра 1
.def PIN1       = R18	; Правильная цифра 2
.def PIN2       = R19	; Правильная цифра 3
.def PIN3       = R20	; Правильная цифра 4
.def SPIN0      = R21	; Вводимая  цифра 1
.def SPIN1      = R22	; Вводимая  цифра 2
.def SPIN2      = R23	; Вводимая  цифра 3
.def SPIN3      = R24	; Вводимая  цифра 4
.def WRONG      = R25	; Сколько введено ошибочных пинкодов
.def DIGIT      = R26	; Какой разряд сейчас вводим
.def SHOW       = R27	; Какой разряд сейчас показываем
.def DEL2SEC    = R17	; Счётчик для задежрки 2 секунды
.def DEL250MS   = R29	; Счётчик для задержки 250 мс
.def INPDLOOP   = R30	; Индикатор зажата ли PD7
.def DEL125MS   = R31 
.def BLINK      = R15


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

; =====================================================
; ЗАДЕРЖКА 250 мс (25 раз по 10 мс)
; =====================================================
delay25:
    LDI  TMP, 25
delay_25sb:
    CALL delay
    DEC  TMP
    BRNE delay_25sb
    RET
    
; =====================================================
; ЗАДЕРЖКА 10 мс
; =====================================================
delay:
    PUSH TMP
    LDI  TMP, 193
    MOV  R7, TMP
    LDI  TMP, 101
    MOV  R8, TMP
delay_sb:
    NOP
    DEC  R8
    NOP
    BRNE delay_sb
    INC  R7
    BRNE delay_sb
    NOP
    NOP
    NOP
    NOP
    POP  TMP
    RET

; =====================================================
; РАСЧЁТ ЗАДЕРЖЕК ЗАЖАТОЙ КНОПКИ PD1 ИЛИ PD0
; =====================================================
calc_delay:
	INC  DEL125MS
	CPI  DEL125MS, 20
	CALL show_blink_num
    IN   TMP, PIND
    ANDI TMP, 0x03
    CPI  TMP,  0x00
    BREQ reset_delay
    CPI  TMP,  0x03
    BREQ reset_delay
    INC  DEL2SEC
    CPI  DEL2SEC, 100
    BRGE pdsdelay
    CPI  INPDLOOP, 0x01
    BRGE pdsdelay
    RET
pdsdelay:
    LDI INPDLOOP, 0x01
    INC DEL250MS
    CPI DEL250MS, 13
    BREQ pdsloop
    RET
pdsloop:
    LDI DEL250MS, 0x00
    CPI TMP, 0x01
    BREQ increase_digit
    BRNE decrease_digit
reset_delay:
    LDI INPDLOOP, 0x00
    LDI DEL250MS, 0x00
    LDI DEL2SEC,    0x00
return:
    RET

; =====================================================
; ОБРАБОТКА НАЖАТИЙ КНОПКО PD1 И PD0
; =====================================================
check_buttons:
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
    dEC SPIN3
    RET
   
; =====================================================
; EEPROM
; =====================================================
eeprom_read:
    ; Считываем PIN0
    LDI  TMP, 0x00
    OUT  EEARH, TMP
    LDI  TMP, 0x00
    OUT  EEARL, TMP
    SBI  EECR, EERE
    IN   PIN0, EEDR

    ; Считываем PIN1
    LDI  TMP, 0x00
    OUT  EEARH, TMP
    LDI  TMP, 0x01
    OUT  EEARL, TMP
    SBI  EECR, EERE
    IN   PIN1, EEDR

    ; Считываем PIN2
    LDI  TMP, 0x00
    OUT  EEARH, TMP
    LDI  TMP, 0x02
    OUT  EEARL, TMP
    SBI  EECR, EERE
    IN   PIN2, EEDR

    ; Считываем PIN3
    LDI  TMP, 0x00
    OUT  EEARH, TMP
    LDI  TMP, 0x03
    OUT  EEARL, TMP
    SBI  EECR, EERE
    IN   PIN3, EEDR

    RET

; =====================================================
; RESET
; =====================================================
reset:
    LDI  TMP, HIGH(RAMEND)
    OUT  SPH, TMP  
    LDI  TMP, LOW(RAMEND)
    OUT  SPL, TMP 
    
    ; Настройка PORTA на выход
    SER  TMP
    OUT  DDRA, TMP
    CLR  TMP
    OUT  PORTA, TMP
    
    ; Настройка PORTB на выход
    SER  TMP
    OUT  DDRB, TMP
    CLR  TMP
    OUT  PORTB, TMP
    
    ; Настроим PORTC для сегментов (A-G, DP)
    SER  TMP
    OUT  DDRC, TMP
    OUT  PORTC, TMP
    
    ; PD0, PD1, PD2, PD3 - вход
    LDI  TMP, 0xF0
    OUT  DDRD, TMP
    CLR  TMP
    OUT  PORTD, TMP
    
    ; начальные значения
    LDI  WRONG, 0x00
    LDI  DIGIT, 0x08
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
	LDI BLINK, 0x00
	LDI DEL125MS, 0x00

    ; PIN читаем из EEPROM
    ;CALL eeprom_read
    
    ; INT0 и INT1
    LDI R16, 0x0F
    OUT MCUCR, R16

    ; разрешение INT0, INT1
    LDI R16, 0xC0
    OUT GICR, R16
    OUT GIFR, R16
    
    ; Timer0
    LDI TMP, 0x0F
    OUT TCCR0, TMP
    LDI TMP, 255
    OUT OCR0, TMP

    ; Timer2	
    LDI TMP, 0x0F
    OUT TCCR2, TMP
    LDI TMP, 195
    OUT OCR2, TMP

    ; Включаем сразу оба прерывания
    LDI TMP, 0x82
    OUT TIMSK, TMP

    SEI
    

  
; =====================================================
; ОСНОВНОЙ ЦИКЛ
; =====================================================  
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
    
; =====================================================
; ОСНОВНОЙ ЦИКЛ
; =====================================================  
correct_loop:
   
    LDI  SPIN0, 0x09
    LDI  SPIN1, 0x09
    LDI  SPIN2, 0x09
    LDI  SPIN3, 0x09
    LDI TMP,  0x80
    OUT PORTA, TMP
    RJMP loop
   
; =====================================================
; ОСНОВНОЙ ЦИКЛ
; =====================================================  
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

; =====================================================
; ОСНОВНОЙ ЦИКЛ
; =====================================================  
wrong_pin:
   INC WRONG
   CPI WRONG, 0x03
   BREQ lock

   ; включаем индикацию ошибки PA6
   LDI TMP, 0x40
   OUT PORTA, TMP

   LDI INPDLOOP, 0x02
   LDI DEL2SEC,  0x00
   LDI DEL250MS, 0x00
   RET

wrong_wait_loop:
    ; выводим только PA6, индикаторы не показываем
    LDI TMP, 0x40
    OUT PORTA, TMP
    CPI WRONG, 0xFF
    BREQ correct_loop
    RJMP loop

    
; =====================================================
; ОСНОВНОЙ ЦИКЛ
; =====================================================  
lock:
   LDI TMP,  0xC0
   OUT PORTA, TMP
l: 
   RJMP l

; =====================================================
; ОСНОВНОЙ ЦИКЛ
; =====================================================  
show_digit:
    CP   SHOW, DIGIT
    BRNE show_num
	RET
show_num:
    CALL code_to_portc
    MOV  TMP, SHOW
    OUT  PORTA, TMP
	LDI  TMP, 0x00
    OUT  PORTA, TMP
    RET

; =====================================================
; ОСНОВНОЙ ЦИКЛ
; =====================================================  
show_blink_digit:
	CPI BLINK, 0xFF
	BREQ blink_return
    CPI DIGIT, 0x01
    BREQ blink0
    CPI DIGIT, 0x02
    BREQ blink1
    CPI DIGIT, 0x04
    BREQ blink2
    CPI DIGIT, 0x08
    BREQ blink3
blink0:
    MOV TMP, SPIN0
    RJMP show_blink_num
blink1:
    MOV TMP, SPIN1
    RJMP show_blink_num
blink2:
    MOV TMP, SPIN2
    RJMP show_blink_num
blink3:
    MOV TMP, SPIN3
show_blink_num:
	LDI TMP, 0xFF
	EOR  BLINK, TMP
	CPI  BLINK, 0x00
	BREQ blink_return
    MOV SHOW, DIGIT
    CALL code_to_portc
    OUT  PORTA, SHOW
	LDI TMP, 0xFF
	EOR  BLINK, TMP
blink_return:
    RET

; =====================================================
; ОСНОВНОЙ ЦИКЛ
; =====================================================  
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
   LDI TMP, 0x3F
   OUT PORTC, TMP
   RET

code1:
   LDI TMP, 0x06
   OUT PORTC, TMP
   RET

code2:
   LDI TMP, 0x5B
   OUT PORTC, TMP
   RET

code3:
   LDI TMP, 0x4F
   OUT PORTC, TMP
   RET

code4:
   LDI TMP, 0x66
   OUT PORTC, TMP
   RET

code5:
   LDI TMP, 0x6D
   OUT PORTC, TMP
   RET

code6:
   LDI TMP, 0x7D
   OUT PORTC, TMP
   RET

code7:
   LDI TMP, 0x07
   OUT PORTC, TMP
   RET

code8:
   LDI TMP, 0x7F
   OUT PORTC, TMP
   RET

code9:
   LDI TMP, 0x6F
   OUT PORTC, TMP
   RET
   
; =====================================================
; ПРЕРЫВАНИЯ
; =====================================================
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


    CALL show_blink_digit

timer0_exit:
    POP  TMP
    MOV  SHOW, TMP
    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI 

TIMER2_COMP_ISR:
    PUSH TMP
    IN   TMP, SREG
    PUSH TMP
    MOV  TMP, SHOW
    PUSH TMP

    ; режим ошибки на 20 секунд
    CPI  INPDLOOP, 0x02
    BREQ error_mode_timer2
    
    CPI  WRONG, 0xFF
    BREQ error_mode_timer2

    ; обычный режим кнопок
    CPI  INPDLOOP, 0x00
    BRNE skip_check
    CALL check_buttons
skip_check:
    CALL calc_delay
    RJMP timer2_exit

error_mode_timer2:
    ; Timer2 ~ 20 мс
    INC  DEL2SEC
    CPI  DEL2SEC, 50
    BRNE timer2_exit

    ; прошла 1 секунда
    LDI  DEL2SEC, 0x00
    INC  DEL250MS
    CPI  DEL250MS, 20
    BRNE timer2_exit

    ; прошло 20 секунд, сброс ошибки и возврат к вводу
    CLR  TMP
    OUT  PORTA, TMP

    LDI  DIGIT, 0x08
    LDI  SHOW,  0x01

    LDI  SPIN0, 0x00
    LDI  SPIN1, 0x00
    LDI  SPIN2, 0x00
    LDI  SPIN3, 0x00

    LDI  DEL2SEC,  0x00
    LDI  DEL250MS, 0x00
    LDI  INPDLOOP, 0x00

timer2_exit:
    POP  TMP
    MOV  SHOW, TMP
    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI
    
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
