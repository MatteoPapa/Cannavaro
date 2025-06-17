import logging

class CheesyVM:
    def __init__(self, code):
        self.MAX_OPS = 3000
        self.optimized_code = ''.join(filter(lambda x: x in ['.', ',', '[', ']', '<', '>', '+', '-'], code))
        self.code = code
        stack, self.jumps = [], {}

        for position, command in enumerate(code):
          if command == "[": stack.append(position)
          if command == "]":
            start = stack.pop()
            self.jumps[start] = position
            self.jumps[position] = start
        
    def __call__(self, STDIN:str):
        try:
            output = self.run(STDIN)
        except Exception as e:
            raise Exception(f'Error on vm {self}: {e}')
        return output
    
    def __repr__(self) -> str:
       return f'''<CheesyVM code={self.code} jumps={self.jumps}>'''

    def __str__(self) -> str:
       return repr(self)

    def run(self, STDIN:str):
        ops = 0
        code_len = len(self.optimized_code)
        memory, eip, esp = [0], 0, 0
        stdin_n = 0
        stdout = ''
        STDIN = STDIN.encode('latin-1')
        
        while ops < self.MAX_OPS and eip < code_len:
            ops += 1
            current = self.optimized_code[eip]
            
            if current == ">":
              esp += 1
              if esp == len(memory): memory.append(0)

            if current == "<":
              esp = 0 if esp <= 0 else esp - 1

            if current == "+":
              memory[esp] = memory[esp] + 1 if memory[esp] < 255 else 0

            if current == "-":
              memory[esp] = memory[esp] - 1 if memory[esp] > 0 else 255

            if current == "[" and memory[esp] == 0: eip = self.jumps[eip]
            if current == "]" and memory[esp] != 0: eip = self.jumps[eip]
            if current == ".": 
                stdout += chr(memory[esp])
            if current == ",":
                memory[esp] = ord(STDIN[stdin_n])
                stdin_n += 1
      
            eip += 1
        
        return stdout
