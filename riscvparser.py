from lark.indenter import Indenter
from lark import Lark, tree
from lark import Tree, Transformer, Token
from lark.visitors import Interpreter,Visitor
from bitarray import bitarray
import pandas as pd
from bitarray.util import int2ba,hex2ba,ba2hex
from lark import Lark, UnexpectedInput, UnexpectedCharacters
from exceptions import *


riscv_parser = Lark.open('./RV32IGrammar.lark', parser='earley', lexer='dynamic')
f3map={
    'ADD':bitarray('000'),
    'SUB':bitarray('000'),
    'ADDI':bitarray('000'),
    'BEQ':bitarray('000'),
    'BNE':bitarray('001'),
    'LW':bitarray('010'),
    'SW':bitarray('010'),
}

f7map={
    'ADD':bitarray('0000000'),
    'SUB':bitarray('0100000'),
}

class LabelTracker(Visitor):
    def __init__(self):
        super().__init__()
        self.labels={}
    def textlabeldec(self, tree):
        self.labels[tree.children[0][:-1]]=4*(tree.children[0].line-1)

class EvalExpressions(Transformer):
    def __init__(self,label_tracker):
        super().__init__()
        self.text_labels=label_tracker.labels
    def norm(self, op):
        return op.upper()
    def get_r_instruction_format(self,opp,rd,rs1,rs2):
        insf = bitarray(2 ** 5)
        addressline=4*(opp.line-1)
        addressline=ba2hex(int2ba(addressline,length=32))
        insf[:-25]=f7map[self.norm(opp.value)]
        insf[-25:-20]=int2ba(int(rs2[1:]),length=5)
        insf[-20:-15]=int2ba(int(rs1[1:]),length=5)
        insf[-15:-12]=f3map[self.norm(opp.value)]
        insf[-12:-7]=int2ba(int(rd[1:]),length=5)
        insf[-7:]=bitarray('0110011')
        return addressline,insf,f'{opp.value} {rd}, {rs1}, {rs2}'
    def get_i_instruction_format(self,opp,rd,rs1,rs2):
        insf = bitarray(2 ** 5)
        addressline=4*(opp.line-1)
        addressline=ba2hex(int2ba(addressline,length=32))
        if rs2.type=='HEX':
            value=hex2ba(rs2.value[2:])[-12:]
            bitvalue=bitarray(12-len(value))
            bitvalue.extend(value)
            insf[:-20]=bitvalue
        elif rs2.type=='INT':
            insf[:-20]=int2ba(int(rs2.value),length=12)
        insf[-20:-15]=int2ba(int(rs1[1:]),length=5)
        insf[-15:-12]=f3map[self.norm(opp.value)]
        insf[-12:-7]=int2ba(int(rd[1:]),length=5)
        insf[-7:]=bitarray('0010011')
        return addressline,insf,f'{opp.value} {rd}, {rs1}, {rs2.value}'
    def get_b_instruction_format(self,opp,rs1,rs2,label):
        insf = bitarray(2 ** 5)
        addressline=4*(opp.line-1)
        targetline=self.text_labels[label]
        offset=int((targetline-addressline)/2)
        offset=int2ba(offset,signed=True,length=12)
        insf[:-25]=bitarray(str(offset[0]))+offset[2:-4]
        insf[-25:-20]=int2ba(int(rs2[1:]),length=5)
        insf[-20:-15]=int2ba(int(rs1[1:]),length=5)
        insf[-15:-12]=f3map[self.norm(opp.value)]
        insf[-12:-7]=offset[-4:]+(bitarray(str(offset[1])))
        insf[-7:]=bitarray('1100011')
        
        addressline=ba2hex(int2ba(addressline,length=32))
        return addressline,insf,f'{opp.value} {rs1}, {rs2}, {label}'
    def get_l_instruction_format(self,opp,rd,rs1,offset):
        insf = bitarray(2 ** 5)
        addressline=4*(opp.line-1)
        addressline=ba2hex(int2ba(addressline,length=32))
        insf[:-20]=int2ba(offset,length=12)
        insf[-20:-15]=int2ba(int(rs1[1:]),length=5)
        insf[-15:-12]=f3map[self.norm(opp.value)]
        insf[-12:-7]=int2ba(int(rd[1:]),length=5)
        insf[-7:]=bitarray('0000011')
        return addressline,insf,f'{opp.value} {rd}, {offset}({rs1})'
    def get_s_instruction_format(self,opp,rs1,rs2,offset):
        insf = bitarray(2 ** 5)
        addressline=4*(opp.line-1)
        addressline=ba2hex(int2ba(addressline,length=32))
        imm=int2ba(offset,length=12)
        insf[:-25]=imm[:-5]
        insf[-25:-20]=int2ba(int(rs2[1:]),length=5)
        insf[-20:-15]=int2ba(int(rs1[1:]),length=5)
        insf[-15:-12]=f3map[self.norm(opp.value)]
        insf[-12:-7]=imm[-5:]
        insf[-7:]=bitarray('0100011')
        return addressline,insf,f'{opp.value} {rs2}, {offset}({rs1})'
    def rtypeins(self, args):
        return self.get_r_instruction_format(args[0],args[1].value,args[3].value,args[5].value)
    def itypeins(self,args):
        return self.get_i_instruction_format(args[0],args[1].value,args[3].value,args[5].children[0])
    def btypeins(self,args):
        return self.get_b_instruction_format(args[0],args[1].value,args[3].value,args[5].value)
    def ltypeins(self,args):
        print(args)
        offset = 0
        src_register = None
        for i in args[3:]:
            if isinstance(i, Tree) and i.data == 'dtypeset':
                imm = i.children[0]
                if imm.type == 'INT':
                    offset = int(imm.value)
                elif imm.type == 'HEX':
                     offset = int(imm.value, 16)
            elif isinstance(i, Token) and i.type == 'REGREF':
                src_register = i.value
        return self.get_l_instruction_format(args[0],args[1].value,src_register,offset)
    def stypeins(self, args):
        offset = 0
        rs1 = None
        rd = args[1].value

        for i in args:
            if isinstance(i, Token) and i.type == 'REGREF':
                rs1 = i.value
            elif isinstance(i, Tree) and i.data == 'dtypeset':
                val = i.children[0]  
                if val.type == 'INT':
                    offset = int(val.value)
                elif val.type == 'HEX':
                    offset = int(val.value[2:], 16)
        return self.get_s_instruction_format(args[0],rs1,args[1].value,offset)
def parse(text,parser):
    try:
        j = parser.parse(text)
        return j
    except UnexpectedInput as u:
        print(u.state)
        exc_class = u.match_examples(parser.parse, {
            TooManyOperands: sample_many,
            IncorrectOperator:sample_ops
        }, use_accepts=True)
        if not exc_class:
            raise IncorrectSyntax(u.get_context(text),u.line, u.column)
        raise exc_class(u.get_context(text), u.line, u.column)
        return
def get_instruction_format(code):
    parse_tree=parse(code,riscv_parser)

    reg_tokens = parse_tree.scan_values(lambda v: isinstance(v, Token) and v.type=='REGREF')
    for i in reg_tokens:
        if int(i.value[1:])>=32:
            raise RegisterOutOfRange(f'"{i.value}"',i.line,i.column)

    ltrack=LabelTracker()
    ltrack.visit(parse_tree)

    
    lref_tokens = parse_tree.scan_values(lambda v: isinstance(v, Token) and v.type=='LABELREF')
    for i in lref_tokens:
        if i.value not in ltrack.labels:
            raise LabelNotExists(f'"{i.value}"',i.line,i.column)

    riscv_transformer=EvalExpressions(ltrack)
    instruction_tree=riscv_transformer.transform(parse_tree)
    df=pd.DataFrame([{"address":subtree.children[0][0],"instruction_format(Binary)":subtree.children[0][1].to01(),"instruction_format(Hex)":f'0x{ba2hex(subtree.children[0][1])}',"basic":subtree.children[0][2]} for subtree in instruction_tree.find_data('instruction')])
    return df