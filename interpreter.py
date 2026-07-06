import pandas as pd
from bitarray.util import int2ba,hex2ba,ba2hex,ba2int
from bitarray import bitarray
import math

oppcode_map={
    '0110011':'r','0010011':'i','0000011':'l','0100011':'s','1100011':'b'
}
def get_alu_i(aval,imm,f3):
    match f3:
        case '000':
            return int2ba(ba2int(aval,signed=True) + ba2int(imm,signed=True),length=32,signed=True)
        case '100':
            return aval ^ imm
        case '110':
            return aval | imm
        case '111':
            return aval & imm
        case '001':
            return aval << ba2int(imm)
        case '101':
            return aval >> ba2int(imm)
        case '010':
            return int2ba(int(int(int2ba(aval,signed=False) < int2ba(imm,signed=False))),length=32)
def get_alu_r(aval,bval,f37):
    match f37:
        case '0000000000':
            return int2ba(ba2int(aval,signed=True) + ba2int(bval,signed=True),length=32,signed=True)
        case '0000100000':
            return int2ba(ba2int(aval,signed=True) - ba2int(bval,signed=True),length=32,signed=True)
        case '1000000000':
            return aval ^ bval
        case '1100000000':
            return aval | bval
        case '1110000000':
            return aval & bval
        case '0010000000':
            return aval << ba2int(bval)
        case '1010000000':
            return aval >> ba2int(bval)
        case '0100000000':
            return int2ba(int(ba2int(aval,signed=False) < ba2int(bval,signed=False)),length=32)
def get_branch_b(pc,imm,aval,bval,f3):
    match f3:
        case '000':
            cond= int2ba(int(aval==bval),length=32)
        case '001':
            cond= int2ba(int(aval!=bval),length=32)
        case '100':
            cond= int2ba(int(aval<bval),length=32)
        case '101':
            cond= int2ba(int(aval>=bval),length=32)
    return cond,int2ba(ba2int(pc)+ba2int(imm<<1),length=32)
def get_load_l(aval,imm):
    return int2ba(ba2int(aval,signed=True) + ba2int(imm,signed=True),length=32,signed=True)
def get_store_s(aval,imm):
    return int2ba(ba2int(aval,signed=True) + ba2int(imm,signed=True),length=32,signed=True)
def get_excycle(ifmt,aval,bval,imm,f3,f7,pc):
    match ifmt:
        case 'i':
            return bitarray(2**5), get_alu_i(aval,imm,f3)
        case 'r':
            return bitarray(2**5), get_alu_r(aval,bval,f3+f7)
        case 'b':
            return get_branch_b(pc,imm,aval,bval,f3)
        case 'l':
            return bitarray(2**5), get_load_l(aval,imm)
        case 's':
            return bitarray(2**5), get_store_s(aval,imm)
def get_lmd_mem(memdf,alu):
    base_address=ba2hex(int2ba(32*math.floor(ba2int(alu)/32),length=32)).upper()
    col=f'Value (+{hex(ba2int(alu)%32)[2:].upper()})'
    return memdf.loc[base_address,col]
def set_lmd_mem(memdf,alu,bval):
    base_address=ba2hex(int2ba(32*math.floor(ba2int(alu)/32),length=32)).upper()
    col=f'Value (+{hex(ba2int(alu)%32)[2:].upper()})'
    print(base_address,col)
    memdf.loc[base_address,col]=ba2hex(bval).upper()
    print(memdf.loc[base_address,col])
    # return memdf
def get_step_run(pc,instr_fmt,ins,memdf,registers):
    ir=hex2ba(instr_fmt)
    pc=hex2ba(pc)
    npc=int2ba(ba2int(pc)+4,length=32)
    areg=registers[ba2int(ir[-20:-15])]
    breg=registers[ba2int(ir[-25:-20])]

    ifmt=oppcode_map[ir[-7:].to01()] 
    if ifmt in 'irl':
        imm_val=ir[:-20]
    elif ifmt == 's':
        imm_val=ir[-32:-25]+ir[-12:-7]
    elif ifmt == 'b':
        imm_val=ir[-32:-25]+ir[-12:-7]
        imm_val=bitarray(imm_val[0])+bitarray(imm_val[-1])+imm_val[1:11]
  
    else:
        raise Exception('later')
    imm=bitarray(str(imm_val[0])*(32-len(imm_val)))
    imm.extend(imm_val)
    cond,alu=get_excycle(ifmt,areg,breg,imm,ir[-15:-12].to01(),ir[:-25].to01(),pc)
    if ba2int(cond)>0:
        pc=alu
    else:
        pc=npc
    cycle_row={"instruction":ins,"IR": ba2hex(ir).upper(), "PC": ba2hex(pc).upper(), "NPC": ba2hex(npc).upper(), "A": ba2hex(areg).upper(), "B": ba2hex(breg).upper(),'Imm':ba2hex(imm).upper(),'cond':ba2hex(cond).upper(),'ALU':ba2hex(alu).upper(),'LMD':None,'Rn':None}
    lmd=None
    if ifmt=='l':
        lmd=get_lmd_mem(memdf,alu)
        cycle_row['LMD']=ba2hex(lmd).upper()
    elif ifmt=='s':
        set_lmd_mem(memdf,alu,breg)
    if ifmt=='l':
        cycle_row['Rn']=ba2hex(lmd).upper()
        registers[ba2int(ir[-12:-7])]=lmd
    elif ifmt in 'ir':
        cycle_row['Rn']=ba2hex(alu).upper()
        registers[ba2int(ir[-12:-7])]=alu
    pc=ba2hex(pc).upper()
    return cycle_row
def get_init_memory():
    memidx=[ba2hex(int2ba(i,length=32,signed=False)).upper() for i in range(0,2047,32)]
    memrow=[{f'Value (+{hex(k*4)[2:].upper()})':'0'*8 for k in range(8)} for i in range(0,2047,32)]
    memdf=pd.DataFrame(memrow,index=memidx)
    memdf.index.rename('Address',inplace=True)
    return memdf
def set_mem(memdf,addr,val):
    base_address=ba2hex(int2ba(32*math.floor(int(addr,16)/32),length=32)).upper()
    col=f'Value (+{hex(int(addr,16)%32)[2:].upper()})'
    memdf.loc[base_address,col]=val.upper()
