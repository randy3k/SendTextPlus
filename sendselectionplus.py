import sublime
import sublime_plugin
import re

class SendSelectionPlusCommand(sublime_plugin.TextCommand):

    # expand selection to {...} when being triggered
    def expand_sel(self, sel):
        esel = self.view.find(r"""^(?:.*(\{(?:(["\'])(?:[^\\]|\\.)*?\2|#.*$|[^\{\}]|(?1))*\})[^\{\}\n]*)+"""
            , self.view.line(sel).begin())
        if self.view.line(sel).begin() == esel.begin():
            return esel

    def run(self, edit):
        settings = sublime.load_settings("SendTextPlus.sublime-settings")
        view = self.view
        cmd = ''
        for sel in [s for s in view.sel()]:
            if sel.empty():
                thiscmd = view.substr(view.line(sel))
                line = view.rowcol(sel.end())[0]
                # if the line ends with {, expand to {...}
                if re.match(r".*\{\s*$", thiscmd):
                    esel = self.expand_sel(sel)
                    if esel:
                        thiscmd = view.substr(esel)
                        line = view.rowcol(esel.end())[0]
                if settings.get("auto_advance", False):
                    view.sel().subtract(sel)
                    pt = view.text_point(line+1,0)
                    view.sel().add(sublime.Region(pt,pt))
            else:
                thiscmd = view.substr(sel)
            cmd += thiscmd +'\n'

        view.run_command("send_text_plus", {"prog": "iTerm", "cmd": cmd})
