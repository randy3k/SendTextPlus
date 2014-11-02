import sublime
import sublime_plugin
import os
import subprocess
import re

def syntax_settings(lang, key, default=None):
    settings = sublime.load_settings("SendTextPlus.sublime-settings")
    ret = None
    plat = sublime.platform()
    if lang:
        lang_settings = settings.get(lang)
        os_settings = lang_settings.get(plat)
        if os_settings:
            ret = os_settings.get(key)
        if not ret:
            ret = lang_settings.get(key)
    if not ret:
        ret = settings.get("default").get(plat).get(key)
    if not ret:
        ret = default
    return ret

def clean(cmd):
    cmd = cmd.expandtabs(4)
    cmd = cmd.rstrip('\n')
    if len(re.findall("\n", cmd)) == 0:
        cmd = cmd.lstrip()
    return cmd

def escape_dq(cmd):
    cmd = cmd.replace('\\', '\\\\')
    cmd = cmd.replace('"', '\\"')
    return cmd

def sendtext(prog, cmd):
    plat = sublime.platform()
    if plat == 'osx':
        if prog == 'Terminal':
            cmd = clean(cmd)
            cmd = escape_dq(cmd)
            args = ['osascript']
            args.extend(['-e', 'tell app "Terminal" to do script "' + cmd + '" in front window\n'])
            subprocess.Popen(args)

        elif prog == "iTerm":
            cmd = clean(cmd)
            cmd = escape_dq(cmd)
            # when cmd ends in a space, iterm does not execute. Thus append a line break.
            if (cmd[-1:] == ' '):
                cmd += '\n'
            args = ['osascript']
            args.extend(['-e', 'tell app "iTerm" to tell the first terminal to tell current session to write text "' + cmd +'"'])
            subprocess.Popen(args)

    if plat == 'linux':
        settings = sublime.load_settings("SendTextPlus.sublime-settings")
        if prog == "tmux":
            progpath = settings.get("tmux", "tmux")
            subprocess.call([progpath, 'set-buffer', cmd + "\n"])
            subprocess.call([progpath, 'paste-buffer', '-d'])

        elif prog == "screen":
            progpath = settings.get("screen", "screen")
            subprocess.call([progpath, '-X', 'stuff', cmd + "\n"])

    elif plat == 'windows':
        raise Exception("not yet supported")

class SendTextPlusCommand(sublime_plugin.TextCommand):
    def get_syntax(self):
        view = self.view
        pt = view.sel()[0].begin() if len(view.sel())>0 else 0
        if view.score_selector(pt, "source.r"):
            return "r"
        elif view.score_selector(pt, "source.python"):
            return "python"
        elif view.score_selector(pt, "source.julia"):
            return "julia"

    def r_expand_sel(self, thiscmd, sel):
        # expand selection to {...} when being triggered
        view = self.view
        esel = sel
        if re.match(r".*\{\s*$", thiscmd):
            esel = view.find(r"""^(?:.*(\{(?:(["\'])(?:[^\\]|\\.)*?\2|#.*$|[^\{\}]|(?1))*\})[^\{\}\n]*)+"""
                    , view.line(sel).begin())
            if view.line(sel).begin() == esel.begin():
                thiscmd = view.substr(esel)
        return (thiscmd, esel)

    def run(self, edit):
        view = self.view
        syntax = self.get_syntax()
        cmd = ''
        for sel in [s for s in view.sel()]:
            if sel.empty():
                thiscmd = view.substr(view.line(sel))
                line = view.rowcol(sel.end())[0]

                if syntax_settings(syntax, "block", False):
                    if syntax == "r":
                        (thiscmd, esel) = self.r_expand_sel(thiscmd, sel)
                        line = view.rowcol(esel.end())[0]
                    elif syntax == "python":
                        pass
                    elif syntax == "julia":
                        pass

                if syntax_settings(syntax, "auto_advance", False):
                    view.sel().subtract(sel)
                    pt = view.text_point(line+1,0)
                    view.sel().add(sublime.Region(pt,pt))
            else:
                thiscmd = view.substr(sel)
            cmd += thiscmd +'\n'


        prog = syntax_settings(syntax, "prog")
        sendtext(prog, cmd)
