all: lc.g4 achurch.py
	make lc
	make exe

lc: lc.g4
	antlr4 -Dlanguage=Python3 -no-listener -visitor lc.g4

exe: achurch.py
	python3.10 achurch.py

clean:
	rm output.png
