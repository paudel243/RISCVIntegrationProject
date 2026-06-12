sample_many = ["""
.global main
.data
vart: .word 0xac
varu: .word 0x55
.text
main:
SW x10, 0(x9), x21
"""]

sample_ops=[
    '''.global main
.data
vart: .word 0xac
varu: .word 0x55
.text
main:
MAX x10, 0(x9), x21'''
]

class RiscSyntaxError(SyntaxError):
    def __str__(self):
        context, line, column = self.args
        return 'Error in line %s column %s: %s.\n%s'% (line, column,self.label,  context)
class TooManyOperands(RiscSyntaxError):
    label = 'Too many operands'
class TooFewOperands(RiscSyntaxError):
    label = 'Too few or incorrectly formatted operands'
class IncorrectOperator(RiscSyntaxError):
    label = 'Not a recognized operator'
class IncorrectSyntax(RiscSyntaxError):
    label = 'Incorrect Syntax'

class RegisterOutOfRange(RiscSyntaxError):
    label = 'Register does not exists'
class LabelNotExists(RiscSyntaxError):
    label = 'Label does not exists'