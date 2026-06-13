# DelphiShell
AI-integrated shell for interacting with DelphiOS.
This is the shell component of DelphiOS, a local AI-integrated operating system currently being developed.
Delphi Shell is a standalone C-based shell, with the ability to act as a natural language to bash command translator. 
This translation aids in bash development or allows for users who may not know how to use shell commands to interact with the shell.
Delphi uses a fine-tuned OpenAI GPT 2.0 model locally hosted on the user's machine and runs on either CPU or GPU. 

Notes: 
- Developing in linux, however, using the makefile in the windows section it should still work. 



## To run and compile:
```bash
git clone https://github.com/Mereck600/DelphiShell.git
```

```bash
make deps
make
make train
make run
```

## Example Delphi Usage: 


Example delphi current input
```bash 
delphi
```
running this command will switch the shell into delphi mode and pass whatever plain text is recieved into the model
For example:
```bash
list files in the current directory
```

Example output:

```
{"mode":"shell","command":"ls -la"}
{"mode":"write_file","path":"hello.py","content":"print('hi')"}
{"mode":"run_file","command":"python3 hello.py"}
{"mode":"answer","text":"I could not safely interpret that request."}

```


Here is what I have currently to run the model alone:

```bash
.venv/bin/python delphi/infer_delphi.py "list files"
{"mode":"shell","command":"ls"}
```


Next Steps:
Practical limitations

A tiny transformer trained from scratch will not be smart at first.

So the best realistic path is:

Start with the tiny GPT-2 config above.
Train on tightly formatted command/action pairs.
Keep rule-based fallback logic in infer_delphi.py.
Only let the model map to a small set of allowed action types.
Add confirmations for dangerous actions like:
rm
overwriting files
recursive moves
package install

