# SendTextPlus for Sublime Text

This package improves [SendText](https://github.com/wch/SendText), particularly for `r`,
`python` and `julia` syntaxes. It supports 

 - Terminal of Mac
 - iTerm 2 of Mac 
 - screen and tmux on Unix machines
 - [Cmder](http://bliker.github.io/cmder) and Cygwin on Windows (see below to configure Cmder)
 - SublimeREPL for R and python syntaxes (it works better with R)

### Installation

Via Package Control.

### Demo
![](https://raw.githubusercontent.com/randy3k/SendTextPlus/master/send_text_plus.gif)

### Usage

- <kbd>cmd</kbd>+<kbd>enter</kbd> (Mac) or <kbd>ctrl</kbd>+<kbd>enter</kbd> (Windows/Linux)

If text is selected, it sends the text to the program selected. If no text is selected, then it sends the current block (if found). Finally, it moves the cursor to the next line.

Terminal is the default for Mac and tmux is the default for Linux. To configure the settings, open Preferences -> Package Settings -> SendTextPlus -> Settings.

Belows are only for `r`, `python` and `julia`.

- <kbd>cmd</kbd>+<kbd>\\</kbd> (Mac) or <kbd>ctrl</kbd>+<kbd>\\</kbd> (Windows/Linux): change working directory


- <kbd>cmd</kbd>+<kbd>b</kbd> (Mac) or <kbd>ctrl</kbd>+<kbd>b</kbd> (Windows/Linux): source current file

SendTextPlus uses Sublime build system to source files, you might have to choose the `SendTextPlus` build system before pressing the keys.

### Cmder settings

Go to `Paste` in the settings, uncheck, "Confirm <enter> keypress" and "Confirm pasting more than..."


### Some Details

- For `r`, blocks are detected by a regular expression for  `{`,`}` pairs. 
- For `julia`, blocks are defined by `begin`, `end` pairs and indentations. 
- For `python`, blocks are detected by indentations, and it is assumed that ipython is used.
