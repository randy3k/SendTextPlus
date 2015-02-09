import sublime
import sublime_plugin
import os
from .sendtext import sendtext, expand_block, escape_dq, get_syntax, syntax_settings


class SendTextPlusCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        cmd = ''
        moved = False
        for sel in [s for s in view.sel()]:
            if sel.empty():
                if syntax_settings(view, "block", False):
                    esel = expand_block(view, sel)
                thiscmd = view.substr(view.line(esel))
                line = view.rowcol(esel.end())[0]
                if syntax_settings(view, "auto_advance", False):
                    view.sel().subtract(sel)
                    pt = view.text_point(line+1, 0)
                    view.sel().add(sublime.Region(pt, pt))
                    moved = True
            else:
                thiscmd = view.substr(sel)
            cmd += thiscmd + '\n'

        sendtext(view, cmd)

        if moved:
            view.show(view.sel())


class SendTextPlusChangeDirCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        fname = view.file_name()
        if not fname:
            sublime.error_message("Save the file!")
            return

        dirname = os.path.dirname(fname)
        syntax = get_syntax(view)

        if syntax == "r":
            cmd = "setwd(\"" + escape_dq(dirname) + "\")"
        elif syntax == "julia":
            cmd = "cd(\"" + escape_dq(dirname) + "\")"
        elif syntax == "python":
            cmd = "cd \"" + escape_dq(dirname) + "\""
        sendtext(view, cmd + "\n")
