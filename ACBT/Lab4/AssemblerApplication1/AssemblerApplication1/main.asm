.def TMP        = R16
.def BLINK      = R17
.def MODE       = R18
.def DA         = R19
.def DB         = R20
.def DC         = R21
.def HA         = R22
.def HB         = R23
.def HC         = R24
.def PA         = R25
.def PB         = R26
.def PPC        = R27
.def TMP2       = R28



.org $0000
    RJMP reset
.org INT0addr
    RJMP EXT_INT0
.org INT1addr
    RJMP EXT_INT1
.org ADCCaddr
    RJMP ADC_ISR
.org OC2addr
    RJMP TIMER2_COMP_ISR
.org OC0addr
    RJMP TIMER0_COMP_ISR


.org $30
reset:
    ; Инициализация стека
    LDI  TMP, HIGH(RAMEND)
    OUT  SPH, TMP
    LDI  TMP, LOW(RAMEND)
    OUT  SPL, TMP
    
    ; PORTA
    ; PA5 = вход ADC5
    ; остальные биты - выход
    LDI  TMP,   0xDF
    OUT  DDRA, TMP
    CLR  TMP
    OUT  PORTA, TMP
    
    ; PORTB - выход для гирлянды
    SER  TMP
    OUT  DDRB, TMP
    CLR  TMP
    OUT  PORTB, TMP
    
    ; PORTC - выход для гирлянды
    SER  TMP
    OUT  DDRC, TMP
    OUT  PORTC, TMP
    
    ; PORTD:
    ; PD2 - INT0 вход
    ; PD3 - INT1 вход
    ; PD4 - OC1B выход
    ; PD7 - OC2  выход
    LDI  TMP, 0x90
    OUT  DDRD, TMP
    CLR  TMP
    OUT  PORTD, TMP
    
    
    LDI  BLINK, 0x00
    LDI  MODE, 0x00
    LDI  DA, 0x01
    LDI  DB, 0x00
    LDI  DC, 0x00
    LDI  HA, 0x01
    LDI  HB, 0x01
    LDI  HC, 0x02
    
    MOV  TMP, DA
    CALL load_time_to_del
    MOV  PA, TMP

    MOV  TMP, DB
    CALL load_time_to_del
    MOV  PB, TMP

    MOV  TMP, DC
    CALL load_time_to_del
    MOV  PPC, TMP
    
    ; Настройка внешних прерываний INT0 и INT1
    ; INT0 и INT1 срабатывают по переднему фронту (0 -> 1)
    LDI  R16, 0x0F
    OUT  MCUCR, R16

    ; Разрешение INT0 и INT1
    ; GICR = 0xC0: включены INT1 и INT0
    LDI  R16, 0xC0
    OUT  GICR, R16
    OUT  GIFR, R16

    ; Timer0
    ; Режим CTC, предделитель 256
    ; OCR0 = 155
    ; Период: 156 * 256 / 8 МГц = 5 мс
    LDI  TMP, 0x0D 
    OUT  TCCR0, TMP
    LDI  TMP, 77
    OUT  OCR0, TMP

    ; Timer2
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
    
    ; АЦП
    ; PA5 = ADC5
    ; AVCC как опорное
    ; левое выравнивание, читаем 8 бит из ADCH
    ; прерывание по завершению преобразования
    ; 8 МГц / 64 = 125 кГц

    LDI  TMP, 0x65
    OUT  ADMUX, TMP

    LDI  TMP, 0x8E
    OUT  ADCSRA, TMP

    ; старт первого преобразования
    SBI  ADCSRA, ADSC
    
    ; Глобальное разрешение прерываний
    SEI


; Основной цикл программы
loop:
   CPI  MODE, 0x00
   BRNE input_loop
   
   MOV  TMP, DA
   CALL load_val_to_tmp
   ANDI TMP, 0XDF
   OUT  PORTA, TMP
   
   MOV  TMP, DB
   CALL load_val_to_tmp
   OUT  PORTB, TMP
   
   MOV  TMP, DC
   CALL load_val_to_tmp
   OUT  PORTC, TMP
   
   RJMP loop
   
input_loop:
   
   LDI  TMP, 0x74
   OUT  PORTC, TMP
   LDI  TMP, 0x08
   OUT  PORTA, TMP
   CLR  TMP
   OUT  PORTA, TMP

   LDI  TMP, 0xF7
   OUT  PORTC, TMP
   LDI  TMP, 0x04
   OUT  PORTA, TMP

   CLR  TMP
   OUT  PORTA, TMP
   
   CPI  BLINK, 50
   BRGE loop
   
   CALL code_to_3_digit
   LDI  TMP, 0x02
   OUT  PORTA, TMP

   CLR  TMP
   OUT  PORTA, TMP
   
   
   CALL code_to_4_digit
   LDI  TMP, 0x01
   OUT  PORTA, TMP

   CLR  TMP
   OUT  PORTA, TMP
   
   RJMP loop

; Определение нужен ли код для вывода минуса
code_to_3_digit:
    CPI  HA, 0x00
    BREQ code_to_3_digit_blank
    MOV  TMP, HA
    ANDI TMP, 0x80
    CPI  TMP, 0x80
    BREQ code_to_3_digit_minus
code_to_3_digit_blank:
    CLR  TMP
    OUT  PORTC, TMP
    RET
code_to_3_digit_minus:
    LDI  TMP, 0x40
    OUT  PORTC, TMP
    RET
    

; Определение кода для значения HA
code_to_4_digit:
    CPI HA, 0x82
    BREQ code_to_4_digit_m2
    CPI HA, 0x81
    BREQ code_to_4_digit_m1
    CPI HA, 0x00
    BREQ code_to_4_digit_0
    CPI HA, 0x01
    BREQ code_to_4_digit_1
    CPI HA, 0x02
    BREQ code_to_4_digit_2
code_to_4_digit_m2:
    LDI  TMP, 0x5B
    OUT  PORTC, TMP
    RET
code_to_4_digit_m1:
    LDI  TMP, 0x06
    OUT  PORTC, TMP
    RET
code_to_4_digit_0:
    LDI  TMP, 0x3F
    OUT  PORTC, TMP
    RET
code_to_4_digit_1:
    LDI  TMP, 0x06
    OUT  PORTC, TMP
    RET
code_to_4_digit_2:
    LDI  TMP, 0x5B
    OUT  PORTC, TMP
    RET
    

; Загружает значение b в TMP по индексу
load_val_to_tmp:
    CPI  TMP, 0x00
    BREQ load_b0
    CPI  TMP, 0x01
    BREQ load_b1
    CPI  TMP, 0x02
    BREQ load_b2
    CPI  TMP, 0x03
    BREQ load_b3
    CPI  TMP, 0x04
    BREQ load_b4
load_b0:
    LDI  TMP, 7
    RET
load_b1:
    LDI  TMP, 1
    RET
load_b2:
    LDI  TMP, 2
    RET
load_b3:
    LDI  TMP, 3
    RET
load_b4:
    LDI  TMP, 4
    RET
    
; Загружает значение задержки p по индексу
load_time_to_del:
    CPI  TMP, 0x00
    BREQ load_p0
    CPI  TMP, 0x01
    BREQ load_p1
    CPI  TMP, 0x02
    BREQ load_p2
    CPI  TMP, 0x03
    BREQ load_p3
    CPI  TMP, 0x04
    BREQ load_p4
load_p0:
    LDI  TMP, 100
    RET
load_p1:
    LDI  TMP, 50
    RET
load_p2:
    LDI  TMP, 33
    RET
load_p3:
    LDI  TMP, 25
    RET
load_p4:
    LDI  TMP, 20
    RET

; Циклический сдвиг влево по набору значений b    
d_inc:
    CPI  TMP, 0x04
    BREQ d_inc_zero
    INC  TMP
    RET
d_inc_zero:
    LDI  TMP, 0x00
    RET

; Циклический сдвиг вправо по набору значений b   
d_dec:
    CPI  TMP, 0x00
    BREQ d_dec_four
    DEC  TMP
    RET
d_dec_four:
    LDI  TMP, 0x04
    RET


; Циклический сдвиг влево/вправо по набору значений b HA раз
ha_step:
    CPI  HA, 0x00
    BREQ ha_step_return

    MOV  TMP2, HA
    ANDI TMP2, 0x80
    CPI  TMP2, 0x80
    BREQ ha_step_minus

    MOV  TMP2, HA
ha_step_plus_loop:
    CPI  TMP2, 0x00
    BREQ ha_step_return
    DEC  TMP2
    CALL d_inc
    RJMP ha_step_plus_loop
ha_step_minus:
    MOV  TMP2, HA
    ANDI TMP2, 0x7F
ha_step_minus_loop:
    CPI  TMP2, 0x00
    BREQ ha_step_return
    DEC  TMP2
    CALL d_dec
    RJMP ha_step_minus_loop
ha_step_return:
    RET
    
; Timer0 вызывается каждые 5 мс
; Вызывает циклический свдвиг для каждого порта, если значение задержки = 0
TIMER0_COMP_ISR:
    PUSH TMP
    IN   TMP, SREG
    PUSH TMP
    
    DEC  PA
    DEC  PB
    DEC  PPC
    
    CPI  PA, 0X00
    BRNE TIMER0_pa_skip
    MOV  TMP, DA
    CALL ha_step
    MOV  DA, TMP
    CALL load_time_to_del
    MOV  PA, TMP
TIMER0_pa_skip:
    CPI  PB, 0X00
    BRNE TIMER0_pb_skip
    MOV  TMP, DB
    CALL d_inc
    MOV  DB,  TMP
    CALL load_time_to_del
    MOV  PB, TMP
TIMER0_pb_skip:
    CPI  PPC, 0X00
    BRNE TIMER0_pc_skip
    MOV  TMP, DC
    CALL d_inc
    CALL d_inc
    MOV  DC,  TMP
    CALL load_time_to_del
    MOV  PPC, TMP
TIMER0_pc_skip:

    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI
 
; Timer2 вызывается каждые 10 мс
; Увеличивает BLINK на 1, если BLINK = 100 задаёти BLINK в 0
TIMER2_COMP_ISR:
    PUSH TMP
    IN   TMP, SREG
    PUSH TMP
    
    CPI  MODE, 0x00
    BREQ timer2_exit

    INC  BLINK
    CPI  BLINK, 100
    BRLO timer2_exit
    LDI  BLINK, 0

timer2_exit:
    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI

; Прерывыание меняет режим работы
EXT_INT0:
    PUSH TMP
    IN   TMP, SREG
    PUSH TMP
    
    LDI  TMP, 1
    EOR  MODE, TMP
    
    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI
   
    
; Ничего не делает   
EXT_INT1:
    PUSH TMP
    IN   TMP, SREG
    PUSH TMP

    
    
    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI
    
; Прерывания АЦП
; Считывает значение с ADCH и записывает в HA
ADC_ISR:
    PUSH TMP
    IN   TMP, SREG
    PUSH TMP

    IN   TMP, ADCH
    
    CPI  TMP, 51
    BRLO adc_isr_m2

    CPI  TMP, 102
    BRLO adc_isr_m1

    CPI  TMP, 153
    BRLO adc_isr_0

    CPI  TMP, 204
    BRLO adc_isr_1

    RJMP adc_isr_2

adc_isr_m2:
    LDI  HA, 0x82
    RJMP adc_restart

adc_isr_m1:
    LDI  HA, 0x81
    RJMP adc_restart

adc_isr_0:
    LDI  HA, 0x00
    RJMP adc_restart

adc_isr_1:
    LDI  HA, 0x01
    RJMP adc_restart

adc_isr_2:
    LDI  HA, 0x02

adc_restart:
    SBI  ADCSRA, ADSC

    POP  TMP
    OUT  SREG, TMP
    POP  TMP
    RETI
