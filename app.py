import json
import streamlit as st
from code_editor import code_editor
from itables.sample_dfs import get_countries
from riscvparser import get_instruction_format
from exceptions import RiscSyntaxError
import pandas as pd
from bitarray import bitarray
from bitarray.util import ba2hex,ba2int
from interpreter import get_init_memory,set_mem,get_step_run

def reload_register_table():
    st.session_state.registerdf = [
        {"Register": f'0x{reg}', "Value (Hex)": ba2hex(val), "Value (Dec)": ba2int(val)}
        for reg, val in st.session_state.registers.items()
    ]

# Register initialization
if 'registers' not in st.session_state:
    st.session_state.registers = {i: bitarray(2 ** 5) for i in range(32)}
if 'memory_idx' not in st.session_state:
    st.session_state.memory_idx = pd.DataFrame()
if 'memory' not in st.session_state:
    st.session_state.memory = get_init_memory()
if 'registerdf' not in st.session_state:
    reload_register_table()
if 'sec' not in st.session_state:
    st.session_state.sec = pd.DataFrame()
if 'current_addr' not in st.session_state:
    st.session_state.current_addr = None
if 'build_id' not in st.session_state:
    st.session_state.build_id = '0'

# code editor config variables
height = [19, 22]
theme = "default"
shortcuts = "vscode"
focus = False
wrap = True
build_btns=[
    {
        "name": "Build",
        "feather": "Tool",
        "primary": True,
        "hasText": True,
        "showWithIcon": True,
        "commands": ["submit"],
        "style": {"bottom": ".44rem", "right": "0.4rem"},
    },
]
editor_btns = [
    {
        "name": "Build",
        "feather": "Tool",
        "primary": True,
        "hasText": True,
        "showWithIcon": True,
        "commands": ["submit"],
        "style": {"bottom": "4rem", "right": "0.4rem"},
    },
    {
        "name": "Run",
        "feather": "Play",
        "primary": True,
        "hasText": True,
        "showWithIcon": True,
        "commands": ["submit"],
        "style": {"bottom": "0.44rem", "right": "0.4rem"},
    },
    {
        "name": "Next",
        "feather": "SkipForward",
        "primary": True,
        "hasText": True,
        "showWithIcon": True,
        "commands": ["sumit"],
        "style": {"bottom": "2rem", "right": "0.4rem"},
    },
    

]
code_text = '''.global main
.text
main:'''
# code editor
response_dict = code_editor(code_text, height=height, theme=theme, shortcuts=shortcuts, focus=focus, buttons=build_btns, options={"wrap": wrap, "showLineNumbers": True})
# show response dict
def run_button():
    # print(code_text)
    st.session_state.registers = {i: bitarray(2 ** 5) for i in range(32)}
    st.session_state.memory =  get_init_memory()
    reload_register_table()
    st.session_state.sec = pd.DataFrame()
    st.session_state.current_addr = None
    for _,row in st.session_state.memory_idx.iterrows():
        set_mem(st.session_state.memory,row['address'],row['hex'])
    df = st.session_state.instructions

    pc=df['address'].min()
    cycle_df=[]
    cycle_ins=[]
    while pc in df['address'].tolist():
        cycle_ins.append(pc)
        row=df.loc[df.address==pc].iloc[0]
        cycle_row=get_step_run(pc,row['instruction_format(Hex)'][2:],row['basic'],st.session_state.memory,st.session_state.registers)
        cycle_df.append(cycle_row)
        pc=cycle_row['PC']
        if pc not in df['address'].tolist():
            near_idx=df['address'].searchsorted(pc,'right')
            if near_idx<=df.index.max():
                pc=df.loc[near_idx,'address']
    st.session_state.sec =pd.DataFrame(cycle_df,index=cycle_ins)
    reload_register_table()
def step_button():
    # print(code_text)
    df = st.session_state.instructions
    pc=st.session_state.current_addr
    print(st.session_state.current_addr)
    cycle_df=st.session_state.sec
    if pc in df['address'].tolist():
        cycle_addr=pc
        row=df.loc[df.address==pc].iloc[0]
        cycle_row=get_step_run(pc,row['instruction_format(Hex)'][2:],row['basic'],st.session_state.memory,st.session_state.registers)
        pc=cycle_row['PC']
        if pc not in df['address'].tolist():
            near_idx=df['address'].searchsorted(pc,'right')
            if near_idx<=df.index.max():
                pc=df.loc[near_idx,'address']
        print(pc)
        st.session_state.current_addr=pc
        print(st.session_state.current_addr)
        cycle_row=pd.Series(cycle_row)
        cycle_row.rename(cycle_addr,inplace=True)
        st.session_state.sec =pd.concat([cycle_df,cycle_row.to_frame().T])
    reload_register_table()
    

print(response_dict)
if len(response_dict['id']) != 0 and (response_dict['type'] == "selection" or response_dict['type'] == "submit" ):
    if st.session_state.build_id!=response_dict['id']:
        st.session_state.build_id=response_dict['id']
        st.session_state.registers = {i: bitarray(2 ** 5) for i in range(32)}
        st.session_state.memory_idx = pd.DataFrame()
        st.session_state.memory = get_init_memory()
        reload_register_table()
        st.session_state.sec = pd.DataFrame()
        st.session_state.current_addr = None
        st.code('Assemble: assembling risc32i sample.')
        code_text = response_dict['text']
        try:
            df, mem_df = get_instruction_format(code_text)
            # df.to_csv('test.csv',index=False)
            st.session_state.current_addr=df['address'].min()
            st.session_state.instructions=df
            st.code('Assemble: operation completed successfully.')
            st.dataframe(df, use_container_width=True)
            

            st.dataframe(mem_df, use_container_width=True)
            st.session_state.memory_idx=mem_df
            for _,row in mem_df.iterrows():
                set_mem(st.session_state.memory,row['address'],row['hex'])
            
            st.session_state.code_built=True

        except RiscSyntaxError as e:
            st.code(e)
            st.code('Assemble: operation completed with errors.')
    st.subheader("Register State")
    st.dataframe(st.session_state.registerdf, use_container_width=True)

    st.subheader("Memory State")
    st.dataframe(st.session_state.memory_idx, use_container_width=True)
    st.dataframe(st.session_state.memory, use_container_width=True)
    st.subheader("Sequential Execution Cycle")
    st.dataframe(st.session_state.sec, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.button('Run', on_click=run_button)
    with col2:
        st.button('Step Run', on_click=step_button)