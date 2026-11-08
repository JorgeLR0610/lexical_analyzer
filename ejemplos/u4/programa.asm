.intel_syntax noprefix
.section .rodata
.Lfmt: .asciz "%ld"
.Lstr: .asciz "%s"
.Ltrue: .asciz "true"
.Lfalse: .asciz "false"
.Ldivision: .asciz "Error: division por cero"
.bss
.text
.globl main
go___init:
push rbp
mov rbp, rsp
sub rsp, 48
xor eax, eax
.Lend___init:
leave
ret
go_doble:
push rbp
mov rbp, rsp
sub rsp, 48
mov QWORD PTR [rbp-8], rbx
mov rax, rdi
mov rbx, rax
# t1 = v0
mov rax, rbx
mov rbx, rax
# t2 = t1 * 2
mov rax, rbx
mov rcx, 2
imul rax, rcx
mov rbx, rax
# return t2
mov rax, rbx
jmp .Lend_doble
xor eax, eax
.Lend_doble:
mov rbx, QWORD PTR [rbp-8]
leave
ret
go_factorial:
push rbp
mov rbp, rsp
sub rsp, 48
mov QWORD PTR [rbp-8], rbx
mov QWORD PTR [rbp-16], r12
mov rax, rdi
mov r12, rax
# t3 = v3
mov rax, r12
mov rbx, rax
# t4 = t3 <= 1
mov rax, rbx
mov rcx, 1
cmp rax, rcx
setle al
movzx rax, al
mov rbx, rax
# ifFalse t4 goto L1
mov rax, rbx
test rax, rax
jz .Lfactorial_L1
# return 1
mov rax, 1
jmp .Lend_factorial
# L1:
.Lfactorial_L1:
# t5 = v3
mov rax, r12
mov rbx, rax
# t6 = v3
mov rax, r12
mov r12, rax
# t7 = t6 - 1
mov rax, r12
mov rcx, 1
sub rax, rcx
mov r12, rax
# t8 = t7
mov rax, r12
mov r12, rax
# param t8
# t9 = call factorial, 1
mov rdi, r12
call go_factorial
mov r12, rax
# t10 = t5 * t9
mov rax, rbx
mov rcx, r12
imul rax, rcx
mov rbx, rax
# return t10
mov rax, rbx
jmp .Lend_factorial
xor eax, eax
.Lend_factorial:
mov rbx, QWORD PTR [rbp-8]
mov r12, QWORD PTR [rbp-16]
leave
ret
main:
push rbp
mov rbp, rsp
sub rsp, 48
mov QWORD PTR [rbp-8], rbx
mov QWORD PTR [rbp-16], r12
mov QWORD PTR [rbp-24], r13
call go___init
# v12 = 0
mov rax, 0
mov rbx, rax
# v13 = 0
mov rax, 0
mov r12, rax
# L2:
.Lmain_L2:
# t11 = v13
mov rax, r12
mov r13, rax
# t12 = t11 < 5
mov rax, r13
mov rcx, 5
cmp rax, rcx
setl al
movzx rax, al
mov r13, rax
# ifFalse t12 goto L3
mov rax, r13
test rax, rax
jz .Lmain_L3
# t13 = v13
mov rax, r12
mov r13, rax
# param t13
# t14 = call doble, 1
mov rdi, r13
call go_doble
mov r13, rax
# t15 = v12 + t14
mov rax, rbx
mov rcx, r13
add rax, rcx
mov rbx, rax
# v12 = t15
mov rax, rbx
mov rbx, rax
# t16 = v13 + 1
mov rax, r12
mov rcx, 1
add rax, rcx
mov r12, rax
# v13 = t16
mov rax, r12
mov r12, rax
# goto L2
jmp .Lmain_L2
# L3:
.Lmain_L3:
# t17 = v12
mov rax, rbx
mov r12, rax
# t18 = t17 == 20
mov rax, r12
mov rcx, 20
cmp rax, rcx
sete al
movzx rax, al
mov r12, rax
# ifFalse t18 goto L4
mov rax, r12
test rax, rax
jz .Lmain_L4
# t19 = v12
mov rax, rbx
mov r12, rax
# t20 = true
mov rax, 1
mov rbx, rax
#  = print t19 int
mov rsi, r12
lea rdi, [rip+.Lfmt]
xor eax, eax
call printf@PLT
# space = print true bool
mov edi, 32
call putchar@PLT
mov rsi, 1
test rsi, rsi
lea rsi, [rip+.Lfalse]
lea rax, [rip+.Ltrue]
cmovne rsi, rax
lea rdi, [rip+.Lstr]
xor eax, eax
call printf@PLT
#  = newline  
mov edi, 10
call putchar@PLT
# goto L5
jmp .Lmain_L5
# L4:
.Lmain_L4:
# t21 = v12
mov rax, rbx
mov r12, rax
# t22 = false
mov rax, 0
mov rbx, rax
#  = print t21 int
mov rsi, r12
lea rdi, [rip+.Lfmt]
xor eax, eax
call printf@PLT
# space = print false bool
mov edi, 32
call putchar@PLT
mov rsi, 0
test rsi, rsi
lea rsi, [rip+.Lfalse]
lea rax, [rip+.Ltrue]
cmovne rsi, rax
lea rdi, [rip+.Lstr]
xor eax, eax
call printf@PLT
#  = newline  
mov edi, 10
call putchar@PLT
# L5:
.Lmain_L5:
# t23 = 6
mov rax, 6
mov rbx, rax
# param 6
# t24 = call factorial, 1
mov rdi, 6
call go_factorial
mov rbx, rax
# t25 = t24
mov rax, rbx
mov rbx, rax
#  = print t25 int
mov rsi, rbx
lea rdi, [rip+.Lfmt]
xor eax, eax
call printf@PLT
#  = newline  
mov edi, 10
call putchar@PLT
# t26 = 7 - 
mov rax, 7
neg rax
mov rbx, rax
# t27 = t26
mov rax, rbx
mov rbx, rax
# t28 = t27 / 3
mov rax, rbx
mov rcx, 3
test rcx, rcx
jz .Lzero
mov rdx, -9223372036854775808
cmp rax, rdx
jne .Ldiv_main_39
cmp rcx, -1
jne .Ldiv_main_39
jmp .Ldiv_main_39_done
.Ldiv_main_39:
cqo
idiv rcx
.Ldiv_main_39_done:
mov rbx, rax
# t29 = t28
mov rax, rbx
mov rbx, rax
# t30 = 7 - 
mov rax, 7
neg rax
mov r12, rax
# t31 = t30
mov rax, r12
mov r12, rax
# t32 = t31 % 3
mov rax, r12
mov rcx, 3
test rcx, rcx
jz .Lzero
mov rdx, -9223372036854775808
cmp rax, rdx
jne .Ldiv_main_43
cmp rcx, -1
jne .Ldiv_main_43
xor eax, eax
jmp .Ldiv_main_43_done
.Ldiv_main_43:
cqo
idiv rcx
mov rax, rdx
.Ldiv_main_43_done:
mov r12, rax
# t33 = t32
mov rax, r12
mov r12, rax
#  = print t29 int
mov rsi, rbx
lea rdi, [rip+.Lfmt]
xor eax, eax
call printf@PLT
# space = print t33 int
mov edi, 32
call putchar@PLT
mov rsi, r12
lea rdi, [rip+.Lfmt]
xor eax, eax
call printf@PLT
#  = newline  
mov edi, 10
call putchar@PLT
xor eax, eax
.Lend_main:
mov rbx, QWORD PTR [rbp-8]
mov r12, QWORD PTR [rbp-16]
mov r13, QWORD PTR [rbp-24]
leave
ret
.Lzero:
lea rdi, [rip+.Ldivision]
call puts@PLT
mov edi, 1
call exit@PLT
ud2
.section .note.GNU-stack,"",@progbits
