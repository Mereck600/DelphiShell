# DelphiShell
AI integrated shell for interacting with DelphiOS
This is the shell component of DelphiOS an local AI integrated operating system.

Notes: 
- Developing in linux, however using the makefile in the windows section it should still work. 
- Transformer architecture is running on CPU will add GPU compatibility soon. 


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

## Other training commands:
```bash
make train
make train TRAIN_ARGS="--init scratch"
make train TRAIN_ARGS="--init pretrained --rebuild-dataset --epochs 8"

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


Current Examples:
```bssh
copy test.py into all folders in test
"go into the test directory and make a file called config.json


```

TODO:
Add widows specific model/training 
make sure it is cross platform

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


Issues I encountered:
General training was dificult with the model not being accuracte for a while
Speed of requests I used to call
```
tokenizer = GPT2TokenizerFast.from_pretrained(str(MODEL_DIR))
model = GPT2LMHeadModel.from_pretrained(str(MODEL_DIR))
```
every shell request which cased a lot of latency because it reloads the tokenizer and model every request

Citations:

[Natural Language to Bash](https://arxiv.org/pdf/2502.06858)


