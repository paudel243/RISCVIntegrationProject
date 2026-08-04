import pandas as pd
from bitarray.util import int2ba,hex2ba,ba2hex,ba2int
from bitarray import bitarray
import math

oppcode_map={
    '0110011':'r','0010011':'i','0000011':'l','0100011':'s','1100011':'b'
}
ireg_order = [
    "IF/ID.IR",
    "IF/ID.NPC",
    "PC",
    "ID/EX.A",
    "ID/EX.B",
    "ID/EX.IR",
    "ID/EX.Imm",
    "ID/EX.NPC",
    "EX/MEM.ALUoutput",
    "EX/MEM.B",
    "EX/MEM.IR",
    "EX/MEM.cond",
    "MEM/WB.ALUoutput",
    "MEM/WB.IR",
    "MEM/WB.LMD",
    "MEM[EX/MEM.ALUOutput]",
    "REGS[MEM/WB.IR[rd]]",
    "rd",
]
pipelinemap_reg=[
    'IF/ID.instruction',
    'IF/ID.address',
    'ID/EX.instruction',
    'ID/EX.address',
    'EX/MEM.instruction',
    'EX/MEM.address',
    'MEM/WB.instruction',
    'MEM/WB.address',
    'WB.instruction',
    'WB.address',
]
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
            return int2ba(int(int(aval < imm)),length=32)
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
    return ba2hex(cond),ba2hex(int2ba(ba2int(pc)+ba2int(imm<<1),length=32))
def get_load_l(aval,imm):
    return ba2hex(int2ba(ba2int(aval,signed=True) + ba2int(imm,signed=True),length=32,signed=True))
def get_store_s(aval,imm):
    return ba2hex(int2ba(ba2int(aval,signed=True) + ba2int(imm,signed=True),length=32,signed=True))
def get_excycle(current,ir,aval,bval,imm,pc):
    oppcode=ir[-7:].to01()
    f3=ir[-15:-12].to01()
    f7=ir[:-25].to01()
    match oppcode:
        case '0010011':
            current['EX/MEM.cond']=ba2hex(bitarray(2**5)).upper()
            current['EX/MEM.ALUoutput']= ba2hex(get_alu_i(aval,imm,f3))
        case '0110011':
            current['EX/MEM.cond']=ba2hex(bitarray(2**5)).upper()
            current['EX/MEM.ALUoutput']=ba2hex(get_alu_r(aval,bval,f3+f7))
        case '1100011':
            current['EX/MEM.cond'] = ba2hex(bitarray(32)).upper()
            current['EX/MEM.ALUoutput'] = ba2hex(bitarray(32)).upper()
        case '0000011':
            current['EX/MEM.cond']=ba2hex(bitarray(2**5)).upper()
            current['EX/MEM.ALUoutput']= get_load_l(aval,imm)
        case '0100011':
            current['EX/MEM.cond']=ba2hex(bitarray(2**5)).upper()
            current['EX/MEM.ALUoutput']= get_store_s(aval,imm)
    current['EX/MEM.IR']=ba2hex(ir)
    current['EX/MEM.B']=ba2hex(bval)

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
def get_base_ir(memdf,pc):
    base_address=ba2hex(int2ba(32*math.floor(ba2int(pc)/32),length=32)).upper()
    col=f'Value (+{hex(ba2int(pc)%32)[2:].upper()})'
    return memdf.loc[base_address,col]
def get_mem_cycle(current,oppcode,memdf,alu,breg):
    if oppcode=='0000011':
        lmd=get_lmd_mem(memdf,alu)
        current['MEM/WB.LMD']=ba2hex(lmd).upper()
        current['MEM[EX/MEM.ALUOutput]']=ba2hex(lmd).upper()
    elif oppcode=='0100011':
        set_lmd_mem(memdf,alu,breg)
        current['MEM/WB.LMD']=None
        current['MEM[EX/MEM.ALUOutput]']=ba2hex(breg).upper()
        print('load',breg,alu)
def get_wb_cyclee(current,oppcode,ir,alu,lmd,registers):
    if oppcode=='0000011':
        lmd=hex2ba(lmd)
        current['REGS[MEM/WB.IR[rd]]']=ba2hex(lmd).upper()
        rd=bitarray('0'*(32-len(ir[-12:-7])))
        rd.extend(ir[-12:-7])
        current['rd']=ba2hex(rd).upper()
        registers[ba2int(ir[-12:-7])]=lmd
    elif oppcode in ('0110011','0010011'):
        current['REGS[MEM/WB.IR[rd]]']=ba2hex(alu).upper()
        rd=bitarray('0'*(32-len(ir[-12:-7])))
        rd.extend(ir[-12:-7])
        current['rd']=ba2hex(rd).upper()
        registers[ba2int(ir[-12:-7])]=alu
def reload_reg(inter_registers):
    inter_registers.update({reg:None for reg in ireg_order})
    inter_registers.update({reg:None for reg in pipelinemap_reg})

def get_cycle(prev_reg,start,ins,memdf,registers,cycle_cnt=0,load_mem_stall=False):
    branching=0
    pipeline_df=[]
    cycle_row={'cycle':cycle_cnt}
    reload_reg(cycle_row)
    pipeline_row={'cycle':cycle_cnt}
    if prev_reg["MEM/WB.IR"] is not None:
        ir = hex2ba(prev_reg["MEM/WB.IR"])
        get_wb_cyclee(cycle_row, ir[-7:].to01(), ir, hex2ba(prev_reg["MEM/WB.ALUoutput"]), prev_reg["MEM/WB.LMD"], registers)
        cycle_row["WB.address"] = prev_reg["MEM/WB.address"]
        cycle_row["WB.instruction"] = prev_reg["MEM/WB.instruction"]
        pipeline_df.append({"cycle": cycle_cnt, "address": prev_reg["MEM/WB.address"], "instruction": prev_reg["MEM/WB.instruction"], "stage": "WB"})

    if prev_reg["EX/MEM.IR"] is not None:
        ir = hex2ba(prev_reg["EX/MEM.IR"])
        get_mem_cycle(cycle_row, ir[-7:].to01(), memdf, hex2ba(prev_reg["EX/MEM.ALUoutput"]), hex2ba(prev_reg["EX/MEM.B"]))
        cycle_row["MEM/WB.IR"] = prev_reg["EX/MEM.IR"]
        cycle_row["MEM/WB.ALUoutput"] = prev_reg["EX/MEM.ALUoutput"]
        cycle_row["MEM/WB.address"] = prev_reg["EX/MEM.address"]
        cycle_row["MEM/WB.instruction"] = prev_reg["EX/MEM.instruction"]
        pipeline_df.append({"cycle": cycle_cnt, "address": prev_reg["EX/MEM.address"], "instruction": prev_reg["EX/MEM.instruction"], "stage": "MEM"})

    if prev_reg['ID/EX.IR'] is not None and (not load_mem_stall):
        get_excycle(cycle_row,hex2ba(prev_reg['ID/EX.IR']),hex2ba(prev_reg['ID/EX.A']),hex2ba(prev_reg['ID/EX.B']),hex2ba(prev_reg['ID/EX.Imm']),hex2ba(prev_reg['ID/EX.NPC']))
        cycle_row['EX/MEM.address']=prev_reg['ID/EX.address']
        cycle_row['EX/MEM.instruction']=prev_reg['ID/EX.instruction']
        pipeline_row.update({'address':prev_reg['ID/EX.address'],'instruction':prev_reg['ID/EX.instruction'],'stage':'EX'})
        pipeline_df.append(pipeline_row.copy())


    if prev_reg['IF/ID.IR'] is not None and (not load_mem_stall):
        ir=hex2ba(prev_reg['IF/ID.IR'])
        cycle_row['ID/EX.A']=ba2hex(registers[ba2int(ir[-20:-15])])
        cycle_row['ID/EX.B']=ba2hex(registers[ba2int(ir[-25:-20])])
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
        cycle_row['ID/EX.Imm']=ba2hex(imm).upper()
        cycle_row['ID/EX.IR']=prev_reg['IF/ID.IR']
        cycle_row['ID/EX.NPC']=prev_reg['IF/ID.NPC']
        cycle_row['ID/EX.address']=prev_reg['IF/ID.address']
        cycle_row['ID/EX.instruction']=prev_reg['IF/ID.instruction']
        pipeline_row.update({'address':prev_reg['IF/ID.address'],'instruction':prev_reg['IF/ID.instruction'],'stage':'ID'})
        pipeline_df.append(pipeline_row.copy())
    print(prev_reg['PC'], start, load_mem_stall, cycle_cnt)
    if ((prev_reg['PC'] is not None) or (start is not None)) and (not load_mem_stall):
        print('IFS', prev_reg['PC'], start, load_mem_stall, cycle_cnt)
        if prev_reg['PC'] is None:
            pc = start.upper()
        else:
            pc = prev_reg['PC'].upper()
        ir_hex = get_base_ir(memdf, hex2ba(pc))
        ir = hex2ba(ir_hex)
        next_pc = ba2hex(int2ba(ba2int(hex2ba(pc)) + 4, length=32)).upper()
        if ir[-7:].to01() == '1100011':
            rs1 = ba2int(ir[-20:-15])
            rs2 = ba2int(ir[-25:-20])

            aval = registers[rs1]
            bval = registers[rs2]

            imm_val = ir[-32:-25] + ir[-12:-7]
            imm_val = bitarray(imm_val[0]) + bitarray(imm_val[-1]) + imm_val[1:11]

            imm = bitarray(str(imm_val[0]) * (32 - len(imm_val)))
            imm.extend(imm_val)
  
            if prev_reg['ID/EX.IR'] is not None:
                ex_ir = hex2ba(prev_reg['ID/EX.IR'])
                if ex_ir[-7:].to01() in ('0110011','0010011'):
                    rd = ba2int(ex_ir[-12:-7])
                    if rd != 0:
                        if ex_ir[-7:].to01() == '0110011':
                            value = get_alu_r(hex2ba(prev_reg['ID/EX.A']), hex2ba(prev_reg['ID/EX.B']), ex_ir[-15:-12].to01()+ex_ir[:-25].to01())
                        else:
                            value = get_alu_i(hex2ba(prev_reg['ID/EX.A']), hex2ba(prev_reg['ID/EX.Imm']), ex_ir[-15:-12].to01())

                        if rd == rs1:
                            aval = value

                        if rd == rs2:
                            bval = value
            if prev_reg['IF/ID.IR'] is not None:
                prev_ir = hex2ba(prev_reg['IF/ID.IR'])
                prev_opcode = prev_ir[-7:].to01()

                if prev_opcode == '0010011':
                    rd = ba2int(prev_ir[-12:-7])

                    if rd != 0:
                        prev_rs1 = ba2int(prev_ir[-20:-15])
                        prev_imm = prev_ir[:-20]

                        prev_imm = bitarray(str(prev_imm[0])*(32-len(prev_imm))) + prev_imm
                        value = get_alu_i(registers[prev_rs1], prev_imm, prev_ir[-15:-12].to01())
                        if rd == rs1:
                            aval = value
                        if rd == rs2:
                            bval = value
            cond, target = get_branch_b(hex2ba(pc), imm,aval,bval,ir[-15:-12].to01())
            print("IMM =", ba2int(imm), ba2hex(imm))
            print("BRANCH:", cond, target)
            if cond == "00000001":
                next_pc = target
                branching = 2
            else:
                branching = 1
        cycle_row["PC"] = next_pc
        cycle_row["IF/ID.IR"] = ir_hex
        cycle_row["IF/ID.NPC"] = pc
        cycle_row["IF/ID.address"] = pc
        cycle_row["IF/ID.instruction"] = ins

        pipeline_row.update({"address": pc,"instruction": ins,"stage": "IF"})
        pipeline_df.append(pipeline_row.copy())
     
    if load_mem_stall:
        cycle_row["IF/ID.IR"]=prev_reg["IF/ID.IR"]
        cycle_row["IF/ID.NPC"]=prev_reg["IF/ID.NPC"]
        cycle_row["PC"]=prev_reg["PC"]
        cycle_row["ID/EX.A"]=prev_reg["ID/EX.A"]
        cycle_row["ID/EX.B"]=prev_reg["ID/EX.B"]
        cycle_row["ID/EX.IR"]=prev_reg["ID/EX.IR"]
        cycle_row["ID/EX.Imm"]=prev_reg["ID/EX.Imm"]
        cycle_row["ID/EX.NPC"]=prev_reg["ID/EX.NPC"]
        cycle_row['IF/ID.instruction']=prev_reg['IF/ID.instruction']
        cycle_row['IF/ID.address']=prev_reg['IF/ID.address']
        cycle_row['ID/EX.instruction']=prev_reg['ID/EX.instruction']
        cycle_row['ID/EX.address']=prev_reg['ID/EX.address']

    return pipeline_df,cycle_row,branching

def get_init_memory_pipe():
    memidx=[ba2hex(int2ba(i,length=32,signed=False)).upper() for i in range(0,8191,32)]
    memrow=[{f'Value (+{hex(k*4)[2:].upper()})':'0'*8 for k in range(8)} for i in range(0,8191,32)]
    memdf=pd.DataFrame(memrow,index=memidx)
    memdf.index.rename('Address',inplace=True)
    return memdf
def set_mem_pipe(memdf,addr,val):
    base_address=ba2hex(int2ba(32*math.floor(int(addr,16)/32),length=32)).upper()
    col=f'Value (+{hex(int(addr,16)%32)[2:].upper()})'
    memdf.loc[base_address,col]=val.upper()
def set_pnt_registers(registers):
    register_list = [
        "IF/ID.IR",
        "IF/ID.NPC",
        "ID/EX.A",
        "ID/EX.B",
        "ID/EX.IR",
        "ID/EX.Imm",
        "ID/EX.NPC",
        "EX/MEM.ALUoutput",
        "EX/MEM.B",
        "EX/MEM.IR",
        "EX/MEM.cond",
        'IF/ID.instruction',
        'IF/ID.address',
        'ID/EX.instruction',
        'ID/EX.address',
        'EX/MEM.instruction',
        'EX/MEM.address',
    ]
    for reg in register_list:
        registers[reg]=None
def forward_data(cycle_reg,prev_stall):
    load_mem_stall=False
    if (cycle_reg['EX/MEM.IR'] is not None) and (cycle_reg['ID/EX.IR'] is not None):
        ir1=hex2ba(cycle_reg['EX/MEM.IR'])
        ir2=hex2ba(cycle_reg['ID/EX.IR'])
        print(cycle_reg['ID/EX.instruction'],cycle_reg['EX/MEM.instruction'],ir2[-7:].to01(),ir1[-7:].to01(),ir2[-20:-15],ir1[-12:-7])

        if (ir1[-7:].to01() in ('0110011','0010011')) and (ir2[-7:].to01() in ('0110011','0010011','0000011','0100011','1100011')) and (ir1[-12:-7]==ir2[-20:-15]) and (ba2int(ir1[-12:-7])>0):
            cycle_reg['ID/EX.A']=cycle_reg["EX/MEM.ALUoutput"]
            print('forwarding',cycle_reg['EX/MEM.instruction'],'to',cycle_reg['ID/EX.instruction'],'EX',cycle_reg["EX/MEM.ALUoutput"])
        if (ir1[-7:].to01() in ('0110011','0010011')) and (ir2[-7:].to01() in ('0100011','1100011','0110011')) and (ir1[-12:-7]==ir2[-25:-20]) and (ba2int(ir1[-12:-7])>0):
            cycle_reg['ID/EX.B']=cycle_reg["EX/MEM.ALUoutput"]
            print('forwarding',cycle_reg['EX/MEM.instruction'],'to',cycle_reg['ID/EX.instruction'],'EX',cycle_reg["EX/MEM.ALUoutput"])
        if (not prev_stall) and (ir1[-7:].to01() in ('0000011')) and (ir2[-7:].to01() in ('0100011','1100011','0110011')) and (ir1[-12:-7]==ir2[-25:-20]) and (ba2int(ir1[-12:-7])>0):
            load_mem_stall=True
            # cycle_reg['ID/EX.B']=cycle_reg["EX/MEM.ALUoutput"]
            print('stalling',cycle_reg['EX/MEM.instruction'],'to',cycle_reg['ID/EX.instruction'],'EX')
        if (not prev_stall) and (ir1[-7:].to01() in ('0000011')) and (ir2[-7:].to01() in ('0110011','0010011','0000011','0100011','1100011')) and (ir1[-12:-7]==ir2[-20:-15]) and (ba2int(ir1[-12:-7])>0):
            load_mem_stall=True
            print('stalling',cycle_reg['EX/MEM.instruction'],'to',cycle_reg['ID/EX.instruction'],'EX')
        
    if (cycle_reg['MEM/WB.IR'] is not None) and (cycle_reg['ID/EX.IR'] is not None):
        ir1=hex2ba(cycle_reg['MEM/WB.IR'])
        ir2=hex2ba(cycle_reg['ID/EX.IR'])
        if (ir1[-7:].to01() in ('0110011','0010011','0000011')) and (ir2[-7:].to01() in ('0110011','0010011','0000011','0100011','1100011')) and (ir1[-12:-7]==ir2[-20:-15]) and (ba2int(ir1[-12:-7])>0):
            cycle_reg['ID/EX.A']=cycle_reg["MEM/WB.ALUoutput"]
            print('forwarding',cycle_reg['MEM/WB.instruction'],'to',cycle_reg['ID/EX.instruction'],'MEM',cycle_reg["MEM/WB.ALUoutput"])
        if (ir1[-7:].to01() in ('0110011','0010011','0000011')) and (ir2[-7:].to01() in ('0100011','1100011','0110011')) and (ir1[-12:-7]==ir2[-25:-20]) and (ba2int(ir1[-12:-7])>0):
            cycle_reg['ID/EX.B']=cycle_reg["MEM/WB.ALUoutput"]
            print('forwarding',cycle_reg['MEM/WB.instruction'],'to',cycle_reg['ID/EX.instruction'],'MEM',cycle_reg["MEM/WB.ALUoutput"])
        if (ir1[-7:].to01() in ('0000011')) and (ir2[-7:].to01() in ('0100011','1100011','0110011')) and (ir1[-12:-7]==ir2[-25:-20]) and (ba2int(ir1[-12:-7])>0):
            cycle_reg['ID/EX.A']=cycle_reg["MEM/WB.LMD"]
        if (ir1[-7:].to01() in ('0000011')) and (ir2[-7:].to01() in ('0110011','0010011','0000011','0100011','1100011')) and (ir1[-12:-7]==ir2[-20:-15]) and (ba2int(ir1[-12:-7])>0):
            cycle_reg['ID/EX.B']=cycle_reg["MEM/WB.LMD"]
    
    return load_mem_stall