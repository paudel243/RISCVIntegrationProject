# RISCV Integrating Case Project Milestone 2
#### Members:
- Miguel Jusayan Puig
- Dennis Paulo S. Delgado

**Milestone 2 Demo Video**: [link](https://youtu.be/YT7wjEmbsKg)
### Steps to run locally
install dependencies
```pip install -r requirements.txt```

Requirement: Be in working directory
run through streamlit cli (installed in the dependencies)
```streamlit run app.py```


### Milestone 2 updates:
- Pipelining
- add ABI registers to the parser
- implemented single step instruction execution and full execution
- GUI 
- Initial Execution Draft
- Added Operations






# RISCV Integrating Case Project Milestone 1
#### Members:
- Miguel Jusayan Puig
- Dennis Paulo S. Delgado

**Milestone 1 Demo Video**: [link](https://youtu.be/hq5VAU6Iv0M)
### Steps to run locally
install dependencies
```pip install -r requirements.txt```

Requirement: Be in working directory
run through streamlit cli (installed in the dependencies)
```streamlit run app.py```


### Milestone 1:
- Program Input
- Opcode Conversion
- Error Handling
- Dictionary through Lark 
- Web-Based IDE


#### Instruction Format Conversion
Supports only I,B,R,S instructions for word as of the moment. Specifically covers the following operations: ADD, SUB, LW, SW, ADDI, BEQ, BNE.
Only supports .data, .text, .word, and .global for the directives as of the moment.
