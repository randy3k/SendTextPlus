# SendTextPlus for Sublime Text

This package improves [SendText](https://github.com/wch/SendText), particularly for `r`,
`python` and `julia` syntaxes. It supports 

 - Terminal of Mac
 - iTerm 2 of Mac 
 - screen and tmux on Unix machines.

### Installation

Via Package Control.

### Demo
![](https://raw.githubusercontent.com/randy3k/SendTextPlus/master/sendtextplus.gif)

### Usage

`cmd+enter` (Mac) or `ctrl+enter` (Windows/Linux)

If text is selected, it sends the text to the program selected. If no text is selected, then it sends the current block (if found). Finally, it moves the cursor to the next line.

Terminal is the default for Mac and tmux is the default for Linux. To configure the settings, open Preferences -> Package Settings -> SendTextPlus -> Settings.

