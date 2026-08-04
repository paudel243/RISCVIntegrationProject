from lark.indenter import Indenter
from lark import Lark, tree
from lark import Tree, Transformer, Token
from lark.visitors import Interpreter,Visitor
from bitarray import bitarray
import pandas as pd
from bitarray.util import int2ba,hex2ba,ba2hex,ba2int
from lark import Lark, UnexpectedInput, UnexpectedCharacters
from exceptions import *
import heapq


riscv_parser = Lark.open('./RV32IGrammar.lark', parser='earley', lexer='dynamic')
f3map={
    'ADD':bitarray('000'),
    'SUB':bitarray('000'),
    'XOR':bitarray('100'),
    'OR':bitarray('110'),
    'AND':bitarray('111'),
    'SLL':bitarray('001'),
    'SRL':bitarray('101'),
    'SLT':bitarray('010'),

    'ADDI':bitarray('000'),
    'XORI':bitarray('100'),
    'ORI':bitarray('110'),
    'ANDI':bitarray('111'),
    'SLLI':bitarray('001'),
    'SRLI':bitarray('101'),
    'SLTI':bitarray('010'),
    
    'BEQ':bitarray('000'),
    'BNE':bitarray('001'),
    'BLT':bitarray('100'),
    'BGE':bitarray('101'),

    'LW':bitarray('010'),
    'SW':bitarray('010'),
}

f7map={
    'ADD':bitarray('0000000'),
    'SUB':bitarray('0100000'),
    'XOR':bitarray('0000000'),
    'OR':bitarray('0000000'),
    'AND':bitarray('0000000'),
    'SLL':bitarray('0000000'),
    'SRL':bitarray('0000000'),
    'SLT':bitarray('0000000'),
}

class AddressTracker(Visitor):
    def __init__(self):
        super().__init__()
        self.labels={}
        self.instruction_address={}
        self.instruction_cnt=0
    def textlabeldec(self, tree):
        self.labels[tree.children[0][:-1]]=tree.children[0].line-1
    def instruction(self, tree):
        self.instruction_address[tree.children[0].children[0].line-1]=4096+4*(self.instruction_cnt)
        self.instruction_cnt+=1
    def label_addr_assign(self):
        for k,v in self.labels.items():
            closest_value = heapq.nsmallest(1, self.instruction_address.keys(), key=lambda x: (v-x)*1000 if x<v else x-v)
            if closest_value[0] >= v:
                self.labels[k]=self.instruction_address[closest_value[0]]
            else:
                self.labels[k]=max(self.instruction_address.values())+4
        

class EvalExpressions(Transformer):
    def __init__(self,addr_tracker):
        super().__init__()
        self.text_labels=addr_tracker.labels
        self.instruction_address=addr_tracker.instruction_address
        self.opp_counter=0
        self.assign_counter=0
    def norm(self, op):
        return op.upper()
    def get_r_instruction_format(self,opp,rd,rs1,rs2):
        insf = bitarray(2 ** 5)
        addressline=self.instruction_address[opp.line-1]
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
        addressline=self.instruction_address[opp.line-1]
        addressline=ba2hex(int2ba(addressline,length=32))
        if rs2.type=='HEX':
            value=hex2ba(rs2.value[2:])[-12:]
            bitvalue=bitarray(12-len(value))
            bitvalue.extend(value)
            insf[:-20]=bitvalue
        elif rs2.type=='INT':
            insf[:-20]=int2ba(int(rs2.value),length=12,signed=True)
        insf[-20:-15]=int2ba(int(rs1[1:]),length=5)
        insf[-15:-12]=f3map[self.norm(opp.value)]
        insf[-12:-7]=int2ba(int(rd[1:]),length=5)
        insf[-7:]=bitarray('0010011')
        return addressline,insf,f'{opp.value} {rd}, {rs1}, {rs2.value}'
    def get_b_instruction_format(self,opp,rs1,rs2,label):
        insf = bitarray(2 ** 5)
        addressline=self.instruction_address[opp.line-1]
        
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
        addressline=self.instruction_address[opp.line-1]
        
        addressline=ba2hex(int2ba(addressline,length=32))
        insf[:-20]=int2ba(offset,length=12)
        insf[-20:-15]=int2ba(int(rs1[1:]),length=5)
        insf[-15:-12]=f3map[self.norm(opp.value)]
        insf[-12:-7]=int2ba(int(rd[1:]),length=5)
        insf[-7:]=bitarray('0000011')
        return addressline,insf,f'{opp.value} {rd}, {offset}({rs1})'
    def get_s_instruction_format(self,opp,rs1,rs2,offset):
        insf = bitarray(2 ** 5)
        addressline=self.instruction_address[opp.line-1]
        
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
    def get_word_assign(self,varname,val):
        memval = bitarray(2 ** 5)
        addressline=4*(self.assign_counter)
        self.assign_counter+=1
        addressline=ba2hex(int2ba(addressline,length=32))
        if val.type=='HEX':
            print(val.value)
            value=hex2ba(val.value[2:])[:32]
            print(value)
            bitvalue=bitarray(32-len(value))
            bitvalue.extend(value)
        elif val.type=='INT':
            bitvalue=int2ba(int(val.value),length=32,signed=True)
        return varname[:-1],addressline,ba2hex(bitvalue)
    def wordassign(self,args):
        print(args)
        return self.get_word_assign(args[0],args[2].children[0])
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

    ltrack=AddressTracker()
    ltrack.visit(parse_tree)
    ltrack.label_addr_assign()

    
    lref_tokens = parse_tree.scan_values(lambda v: isinstance(v, Token) and v.type=='LABELREF')
    for i in lref_tokens:
        if i.value not in ltrack.labels:
            raise LabelNotExists(f'"{i.value}"',i.line,i.column)

    riscv_transformer=EvalExpressions(ltrack)
    instruction_tree=riscv_transformer.transform(parse_tree)
    insdf=pd.DataFrame([{"address":subtree.children[0][0].upper(),"instruction_format(Binary)":subtree.children[0][1].to01(),"instruction_format(Hex)":ba2hex(subtree.children[0][1]).upper(),"basic":subtree.children[0][2]} for subtree in instruction_tree.find_data('instruction')])

    memdf=pd.DataFrame([{"variable":subtree.children[0][0],"address":subtree.children[0][1].upper(),"hex":subtree.children[0][2].upper()} for subtree in instruction_tree.find_data('dataassign')])
    return insdf,memdf