.def TMP        = R20   ; Регистр для временных значений
.def VAR_Y      = R22   ; Текущее значение Y
.def STATE      = R23   ; Состояние гирлянды: 0 или 1
.def MODE       = R24   ; Режим работы гирлянды: 1, 2 или 3
.def VAL1       = R25   ; Значение, выводимое на PORTA
.def VAL2       = R19   ; Значение, выводимое на PORTB
.def NEG_VAR_Y  = R18   ; Значение -Y в прямом коде
.def LAST_Y     = R17   ; Последнее считанное значение Y
.def INPUT_LOCK = R26   ; Блокировка повторного входа в режим ввода


.org $0000
   JMP reset
.org INT0addr
   JMP EXT_INT0
.org INT1addr
   JMP EXT_INT1


; Программная задержка около 10 мс
delay_10ms:
   LDI  R30, 193
   LDI  R29, 101

delay_10ms_sb:
   NOP
   DEC  R29
   NOP
   BRNE delay_10ms_sb
   INC  R30
   BRNE delay_10ms_sb
   NOP
   NOP
   NOP
   NOP
   RET


; Программная задержка около 250 мс
; Выполняется как 25 задержек по 10 мс
delay:
   LDI  TMP, 25

delay_sb:
   CALL delay_10ms
   DEC  TMP
   BRNE delay_sb
   RET


; Чтение режима работы из EEPROM
; Режим хранится по адресу 0x00.
; Допустимые значения: 1, 2, 3.
; Если в EEPROM находится другое значение, выбирается режим 1.
eeprom_read:
   SBIC EECR, EEWE
   RJMP eeprom_read

   CLR TMP
   OUT EEARH, TMP
   OUT EEARL, TMP

   SBI EECR, EERE
   IN  MODE, EEDR

   CPI MODE, 0x01
   BREQ eeprom_read_ok
   CPI MODE, 0x02
   BREQ eeprom_read_ok
   CPI MODE, 0x03
   BREQ eeprom_read_ok

   LDI MODE, 0x01

eeprom_read_ok:
   RET


; Запись текущего режима работы в EEPROM
; MODE записывается по адресу 0x00.
eeprom_write:
   SBIC EECR, EEWE
   RJMP eeprom_write

   CLR TMP
   OUT EEARH, TMP
   OUT EEARL, TMP

   OUT EEDR, MODE

   IN  TMP, SREG
   CLI
   SBI EECR, EEMWE
   SBI EECR, EEWE
   OUT SREG, TMP
   RET


reset:
   ; Инициализация стека
   LDI  TMP, HIGH(RAMEND)
   OUT  SPH, TMP
   LDI  TMP, LOW(RAMEND)
   OUT  SPL, TMP

   ; PORTC — вход для ввода значения Y
   CLR  TMP
   OUT  DDRC, TMP
   OUT  PORTC, TMP

   ; PORTD:
   ; PD0, PD1 — вывод номера текущего режима
   ; PD2 — INT0, переключение режима вперёд
   ; PD3 — INT1, переключение режима назад
   ; PD4 — вывод текущего состояния гирлянды
   ; PD5, PD6 — выходы
   ; PD7 — вход, кнопка входа в режим ввода Y
   LDI  TMP, 0x73
   OUT  DDRD, TMP
   CLR  TMP
   OUT  PORTD, TMP

   ; PORTA и PORTB — выходы для управления гирляндой
   SER  TMP
   OUT  DDRA, TMP
   OUT  DDRB, TMP

   ; Начальные значения переменных
   LDI VAR_Y, 0x71
   LDI INPUT_LOCK, 0x00
   LDI STATE, 0x00

   ; Чтение сохранённого режима из EEPROM
   CALL eeprom_read

   ; Отображение текущего режима и состояния на PORTD
   CALL mode_show
   CALL state_show

   ; Расчёт -Y для режима 3
   CALL calc_negative_y

   ; Настройка внешних прерываний INT0 и INT1
   ; MCUCR = 0x0F:
   ; INT0 и INT1 срабатывают по переднему фронту
   LDI R16, 0x0F
   OUT MCUCR, R16

   ; Разрешение внешних прерываний INT0 и INT1
   ; GICR = 0xC0: включены INT1 и INT0
   LDI R16, 0xC0
   OUT GICR, R16

   ; Сброс возможных флагов внешних прерываний
   OUT GIFR, R16

   ; Глобальное разрешение прерываний
   SEI


; Основной цикл программы
; Проверяет вход в режим ввода Y и выполняет выбранный режим гирлянды
loop:
   ; Если PD7 отпущена, снимаем блокировку повторного ввода
   IN   TMP, PIND
   ANDI TMP, 0b10000000
   CPI  TMP, 0b00000000
   BRNE check_input_start

   CLR  INPUT_LOCK

check_input_start:
   ; Если ввод уже был выполнен, а PD7 всё ещё удерживается,
   ; повторно в режим ввода не входим
   CPI  INPUT_LOCK, 0x01
   BREQ normal_work

   ; Если PD7 нажата, переходим в режим ввода Y
   IN   TMP, PIND
   ANDI TMP, 0b10000000
   CPI  TMP, 0b10000000
   BRNE normal_work

   CALL read_number
   LDI  INPUT_LOCK, 0x01
   RJMP loop

normal_work:
   CPI  MODE, 0x01
   BREQ set_mode_1
   CPI  MODE, 0x02
   BREQ set_mode_2
   CPI  MODE, 0x03
   BREQ set_mode_3

   RJMP loop


; Ввод значения Y с PORTC
; Ввод выполняется при удержании PD7.
; Последнее ненулевое значение с PINC сохраняется в VAR_Y.
read_number:
   CLR LAST_Y

   ; Если PD7 уже отпущена, завершаем ввод
   IN   TMP, PIND
   ANDI TMP, 0b10000000
   CPI  TMP, 0b10000000
   BRNE read_number_done

   ; Ждём, пока на PORTC появится ненулевое значение
   IN   TMP, PINC
   CPI  TMP, 0x00
   BREQ read_number

read_number_capture:
   ; Небольшая задержка
   CALL delay

   ; Если PORTC стал равен 0, завершаем ввод
   IN   TMP, PINC
   CPI  TMP, 0x00
   BREQ read_number_done

   ; Запоминаем последнее считанное значение
   MOV  LAST_Y, TMP

   ; Если PD7 всё ещё нажата, продолжаем считывание
   IN   TMP, PIND
   ANDI TMP, 0b10000000
   CPI  TMP, 0b10000000
   BRNE read_number_done_by_pd7_release

   RJMP read_number_capture

read_number_done_by_pd7_release:
   ; При отпускании PD7 дополнительно считываем текущее значение PINC
   IN   TMP, PINC
   MOV  LAST_Y, TMP

read_number_done:
   ; Сохраняем введённое значение и пересчитываем -Y
   MOV  VAR_Y, LAST_Y
   CALL calc_negative_y
   RET


; Вывод текущих значений гирлянды
; После вывода выполняется задержка 250 мс и переключение STATE.
show:
   OUT PORTA, VAL1
   OUT PORTB, VAL2

   CALL delay

   LDI TMP, 0x01
   EOR STATE, TMP

   CALL state_show

   RJMP loop


; Режим 1
; PORTA и PORTB поочерёдно принимают значения FF/00 и 00/FF.
set_mode_1:
   CPI STATE, 0x00
   BRNE set_negative_mod_1

   LDI VAL1, 0xFF
   LDI VAL2, 0x00
   RJMP show

set_negative_mod_1:
   LDI VAL1, 0x00
   LDI VAL2, 0xFF
   RJMP show


; Режим 2
; PORTA и PORTB поочерёдно принимают значения AA/55 и 55/AA.
set_mode_2:
   CPI STATE, 0x00
   BRNE set_negative_mod_2

   LDI VAL1, 0xAA
   LDI VAL2, 0x55
   RJMP show

set_negative_mod_2:
   LDI VAL1, 0x55
   LDI VAL2, 0xAA
   RJMP show


; Режим 3
; Используется введённое значение Y и рассчитанное значение -Y.
set_mode_3:
   CPI STATE, 0x00
   BRNE set_negative_mod_3

   MOV VAL1, VAR_Y
   MOV VAL2, NEG_VAR_Y
   RJMP show

set_negative_mod_3:
   MOV VAL1, NEG_VAR_Y
   MOV VAL2, VAR_Y
   RJMP show


; Увеличение номера режима
; После режима 3 снова выбирается режим 1.
mode_inc:
   INC MODE
   CPI MODE, 0x04
   BRNE mode_inc_return

   LDI MODE, 0x01

mode_inc_return:
   CALL mode_show
   RET


; Уменьшение номера режима
; После режима 1 выбирается режим 3.
mode_dec:
   DEC MODE
   BRNE mode_dec_skip

   LDI MODE, 0x03

mode_dec_skip:
   CALL mode_show
   RET


; Отображение текущего режима на PD0 и PD1
; Старшие биты PORTD сохраняются без изменений.
mode_show:
   IN  TMP, PORTD
   ANDI TMP, 0b11111100
   OR  TMP, MODE
   OUT PORTD, TMP
   RET


; Отображение состояния гирлянды на PD4
state_show:
   IN  TMP, PORTD
   ANDI TMP, 0b11101111

   MOV R16, STATE
   LSL R16
   LSL R16
   LSL R16
   LSL R16

   OR  TMP, R16
   OUT PORTD, TMP
   RET


; Вычисление значения -Y в прямом коде
; Если модуль Y равен нулю, результат тоже 0.
; Иначе меняется знаковый бит.
calc_negative_y:
   MOV  TMP, VAR_Y
   ANDI TMP, 0x7F
   BREQ calc_negative_y_return

   LDI  TMP, 0x80
   MOV  NEG_VAR_Y, VAR_Y
   EOR  NEG_VAR_Y, TMP
   RET

calc_negative_y_return:
   LDI NEG_VAR_Y, 0x00
   RET


; Прерывание INT0
; Переключение режима вперёд и сохранение режима в EEPROM
EXT_INT0:
   PUSH TMP
   IN   TMP, SREG
   PUSH TMP

   CALL mode_inc
   CALL eeprom_write

   POP  TMP
   OUT  SREG, TMP
   POP  TMP
   RETI


; Прерывание INT1
; Переключение режима назад и сохранение режима в EEPROM
EXT_INT1:
   PUSH TMP
   IN   TMP, SREG
   PUSH TMP

   CALL mode_dec
   CALL eeprom_write

   POP  TMP
   OUT  SREG, TMP
   POP  TMP
   RETI