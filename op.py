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
            cond= int2ba(int(aval==bval),length=32)#BEQ
        case '001':
            cond= int2ba(int(aval!=bval),length=32)#BNE
        case '100':
            cond= int2ba(int(aval<bval),length=32)#BLT
        case '101':
            cond= int2ba(int(aval>=bval),length=32)#BGE
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
    return hex2ba(memdf.loc[base_address,col])
def set_lmd_mem(memdf,alu,bval):
    base_address=ba2hex(int2ba(32*math.floor(ba2int(alu)/32),length=32)).upper()
    col=f'Value (+{hex(ba2int(alu)%32)[2:].upper()})'
    print(base_address,col)
    memdf.loc[base_address,col]=ba2hex(bval).upper()
    print(memdf.loc[base_address,col])
    # return memdf
def get_step_run(pc,instr_fmt,ins,memdf,registers,cycle_cnt=0):
    pipeline_df=[]
    cylce_df=[]
    cycle_row={'address':pc,'instruction':ins,'cycle':cycle_cnt}
    pipeline_row=cycle_row.copy()
    ir=hex2ba(instr_fmt)
    pc=hex2ba(pc)
    npc=int2ba(ba2int(pc)+4,length=32)
    cycle_cnt+=1
    cycle_row.update({'IF/ID.IR':ba2hex(ir).upper(),'IF/ID.NPC':ba2hex(npc).upper(), 'PC':ba2hex(pc).upper(),'cycle':cycle_cnt})
    pipeline_row.update({'stage':'IF','cycle':cycle_cnt})
    pipeline_df.append(pipeline_row.copy())
    cylce_df.append(cycle_row.copy())

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
        # break
    else:
        raise Exception('later')
    imm=bitarray(str(imm_val[0])*(32-len(imm_val)))
    imm.extend(imm_val)
    cycle_cnt+=1
    cycle_row.update({'ID/EX.A':ba2hex(areg).upper(),'ID/EX.B': ba2hex(breg).upper(),'ID/EX.Imm':ba2hex(imm).upper(),'ID/EX.NPC':cycle_row['IF/ID.NPC'],'ID/EX.IR':cycle_row['IF/ID.IR'],'cycle':cycle_cnt})
    pipeline_row.update({'stage':'ID','cycle':cycle_cnt})
    pipeline_df.append(pipeline_row.copy())
    cylce_df.append(cycle_row.copy())


    cond,alu=get_excycle(ifmt,areg,breg,imm,ir[-15:-12].to01(),ir[:-25].to01(),pc)
    cycle_cnt+=1
    cycle_row.update({'EX/MEM.ALUoutput':ba2hex(alu).upper(),'EX/MEM.cond':ba2hex(cond).upper(),'EX/MEM.IR':cycle_row['ID/EX.IR'],'EX/MEM.B':cycle_row['ID/EX.B'],'cycle':cycle_cnt})
    pipeline_row.update({'stage':'EX','cycle':cycle_cnt})
    pipeline_df.append(pipeline_row.copy())
    cylce_df.append(cycle_row.copy())


    if ba2int(cond)>0:
        pc=alu
    else:
        pc=npc
    
    lmd=None
    if ifmt=='l':
        lmd=get_lmd_mem(memdf,alu)
        cycle_row['MEM/WB.LMD']=ba2hex(lmd).upper()
    elif ifmt=='s':
        set_lmd_mem(memdf,alu,breg)
        cycle_row['MEM[EX/MEM.ALUOutput]']=ba2hex(breg).upper()
    
    cycle_cnt+=1
    cycle_row.update({'MEM/WB.IR':cycle_row['EX/MEM.IR'],'MEM/WB.ALUoutput':cycle_row['EX/MEM.ALUoutput'],'cycle':cycle_cnt,'PC':ba2hex(pc).upper()})
    pipeline_row.update({'stage':'MEM','cycle':cycle_cnt})
    pipeline_df.append(pipeline_row.copy())
    cylce_df.append(cycle_row.copy())
    
    if ifmt=='l':
        cycle_row['REGS[MEM/WB.IR[rd]]']=ba2hex(lmd).upper()
        rd=bitarray('0'*(32-len(ir[-12:-7])))
        rd.extend(ir[-12:-7])
        cycle_row['rd']=ba2hex(rd).upper()
        registers[ba2int(ir[-12:-7])]=lmd
    elif ifmt in 'ir':
        cycle_row['REGS[MEM/WB.IR[rd]]']=ba2hex(alu).upper()
        rd=bitarray('0'*(32-len(ir[-12:-7])))
        rd.extend(ir[-12:-7])
        cycle_row['rd']=ba2hex(rd).upper()
        registers[ba2int(ir[-12:-7])]=alu
    pc=ba2hex(pc).upper()

    cycle_cnt+=1
    cycle_row.update({'cycle':cycle_cnt})
    pipeline_row.update({'stage':'WB','cycle':cycle_cnt})
    pipeline_df.append(pipeline_row.copy())
    cylce_df.append(cycle_row.copy())


    return pipeline_df,cylce_df
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