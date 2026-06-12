import json
import streamlit as st
from code_editor import code_editor
from itables.sample_dfs import get_countries
import streamlit as st
from riscvparser import get_instruction_format
from exceptions import RiscSyntaxError


height = [19, 22]
theme="default"
shortcuts="vscode"
focus=False
wrap=True
editor_btns = [{
    "name": "Run",
    "feather": "Play",
    "primary": True,
    "hasText": True,
    "showWithIcon": True,
    "commands": ["submit"],
    "style": {"bottom": "0.44rem", "right": "0.4rem"}
  }]
sample_python_code = '''.global main
.text
main:'''

# code editor
response_dict = code_editor(sample_python_code,  height = height, theme=theme, shortcuts=shortcuts, focus=focus, buttons=editor_btns, options={"wrap": wrap,"showLineNumbers": True})

# show response dict
if len(response_dict['id']) != 0 and ( response_dict['type'] == "selection" or response_dict['type'] == "submit" ):
    # Capture the text part
    st.code('Assemble: assembling risc32i sample.')
    code_text = response_dict['text']
    # print(code_text)
    try:
        df = get_instruction_format(code_text)
        st.code('Assemble: operation completed successfully.') #Captured the code parameter.
        st.dataframe(df, use_container_width=True)
    except RiscSyntaxError as e:
        st.code(e)
        st.code('Assemble: operation completed with errors.')
