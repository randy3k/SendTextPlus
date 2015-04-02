import sublime
import sublime_plugin
import os
import re
import subprocess
import sys


class SyntaxSettings:

    def __init__(self, syntax):
        self.syntax = syntax

    def get(self, key, default=None):
        settings = sublime.load_settings("SendTextPlus.sublime-settings")
        ret = None
        plat = sublime.platform()
        if self.syntax:
            lang_settings = settings.get(self.syntax)
            if lang_settings:
                os_settings = lang_settings.get(plat)
                if os_settings:
                    ret = os_settings.get(key)
                if ret is None:
                    ret = lang_settings.get(key)
        if ret is None:
            ret = settings.get("default").get(plat).get(key)
        if ret is None:
            ret = settings.get("default").get(key)
        if ret is None:
            ret = default
        return ret


class SyntaxMixins:

    def get_syntax(self):
        view = self.view
        pt = view.sel()[0].begin() if len(view.sel()) > 0 else 0
        if view.score_selector(pt, "source.r"):
            return "r"
        elif view.score_selector(pt, "source.python"):
            return "python"
        elif view.score_selector(pt, "source.julia"):
            return "julia"

    def syntax_settings(self):
        syntax = self.get_syntax()
        return SyntaxSettings(syntax)


class SencTextMixins:

    @staticmethod
    def clean(cmd):
        cmd = cmd.expandtabs(4)
        cmd = cmd.rstrip('\n')
        if len(re.findall("\n", cmd)) == 0:
            cmd = cmd.lstrip()
        return cmd

    @staticmethod
    def escape_dq(cmd):
        cmd = cmd.replace('\\', '\\\\')
        cmd = cmd.replace('"', '\\"')
        return cmd

    @staticmethod
    def iterm_version():
        try:
            args = ['osascript', '-e',
                    'tell app "iTerm" to tell the first terminal to set foo to true']
            subprocess.check_call(args)
            return 2.0
        except:
            return 2.9

    def _send_text_terminal(self, cmd):
        cmd = self.clean(cmd)
        cmd = self.escape_dq(cmd)
        args = ['osascript']
        args.extend(['-e', 'tell app "Terminal" to do script "' + cmd + '" in front window'])
        subprocess.Popen(args)

    def _send_text_iterm(self, cmd):
        cmd = self.clean(cmd)
        cmd = self.escape_dq(cmd)
        ver = self.iterm_version()
        if ver == 2.0:
            args = ['osascript', '-e', 'tell app "iTerm" to tell the first terminal ' +
                    'to tell current session to write text "' + cmd + '"']
        else:
            args = ['osascript', '-e', 'tell app "iTerm" to tell the first terminal window ' +
                    'to tell current session to write text "' + cmd + '"']
        subprocess.check_call(args)

    def _send_text_tmux(self, cmd, tmux="tmux"):
        cmd = self.clean(cmd) + "\n"
        n = 200
        chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
        for chunk in chunks:
            subprocess.call([tmux, 'set-buffer', chunk])
            subprocess.call([tmux, 'paste-buffer', '-d'])

    def _send_text_screen(self, cmd, screen="screen"):
        plat = sys.platform
        cmd = self.clean(cmd) + "\n"
        n = 200
        chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
        for chunk in chunks:
            if plat.startswith("linux"):
                chunk = chunk.replace("\\", r"\\")
                chunk = chunk.replace("$", r"\$")
            subprocess.call([screen, '-X', 'stuff', chunk])

    # def _send_text_ahk(self, cmd, progpath="", script="Rgui.ahk"):
    #     cmd = self.clean(cmd)
    #     ahk_path = os.path.join(sublime.packages_path(), 'User', 'R-Box', 'bin', 'AutoHotkeyU32')
    #     ahk_script_path = os.path.join(sublime.packages_path(), 'User', 'R-Box', 'bin', script)
    #     # manually add "\n" to keep the indentation of first line of block code,
    #     # "\n" is later removed in AutoHotkey script
    #     cmd = "\n" + cmd
    #     args = [ahk_path, ahk_script_path, progpath, cmd]
    #     subprocess.Popen(args)

    def send_text(self, cmd):
        view = self.view
        if cmd.strip() == "":
            return
        plat = sublime.platform()
        settings = self.syntax_settings()
        if plat == "osx":
            prog = settings.get("prog", "Terminal")
        if plat == "windows":
            prog = settings.get("prog", "Cmder")
        if plat == "linux":
            prog = settings.get("prog", "tmux")

        if prog == 'Terminal':
            self._send_text_terminal(cmd)

        elif prog == 'iTerm':
            self._send_text_iterm(cmd)

        # elif plat == "osx" and re.match('R[0-9]*$', prog):
        #     cmd = self.clean(cmd)
        #     cmd = self.escape_dq(cmd)
        #     args = ['osascript']
        #     args.extend(['-e', 'tell app "' + prog + '" to cmd "' + cmd + '"'])
        #     subprocess.Popen(args)

        elif prog == "tmux":
            self._send_text_tmux(cmd, settings.get("tmux", "tmux"))

        elif prog == "screen":
            self._send_text_screen(cmd, settings.get("screen", "screen"))

        elif prog == "SublimeREPL":
            cmd = self.clean(cmd)
            external_id = view.scope_name(0).split(" ")[0].split(".", 1)[1]
            sublime.active_window().run_command(
                "repl_send", {"external_id": external_id, "text": cmd})
            return

        # elif plat == "windows" and re.match('R[0-9]*$', prog):
        #     progpath = settings.get(prog, "1" if prog == "R64" else "0")
        #     self._send_text_ahk(cmd, progpath, "Rgui.ahk")

        # elif prog == "Cygwin":
        #     self._send_text_ahk(cmd, "", "Cygwin.ahk")

        # elif prog == "Cmder":
        #     self._send_text_ahk(cmd, "", "Cmder.ahk")


class ExpandBlockMixins:

    def _expand_block_r(self, sel):
        view = self.view
        # expand selection to {...}
        thiscmd = view.substr(view.line(sel))
        if re.match(r".*\{\s*$", thiscmd):
            esel = view.find(
                r"""^(?:.*(\{(?:(["\'])(?:[^\\]|\\.)*?\2|#.*$|[^\{\}]|(?1))*\})[^\{\}\n]*)+""",
                view.line(sel).begin()
            )
            if view.line(sel).begin() == esel.begin():
                sel = esel
        return sel

    def _expand_block_python(self, sel):
        view = self.view
        thiscmd = view.substr(view.line(sel))
        if re.match(r"^[ \t]*\S", thiscmd):
            indentation = re.match(r"^([ \t]*)", thiscmd).group(1)
            row = view.rowcol(sel.begin())[0]
            prevline = view.line(sel.begin())
            lastrow = view.rowcol(view.size())[0]
            while row < lastrow:
                row = row + 1
                line = view.line(view.text_point(row, 0))
                m = re.match(r"^([ \t]*)([^\n\s]+)", view.substr(line))
                if m and len(m.group(1)) <= len(indentation) and \
                        (len(m.group(1)) < len(indentation) or
                            not re.match(r"else|elif|except|finally", m.group(2))):
                    sel = sublime.Region(sel.begin(), prevline.end())
                    break
                elif re.match(r"^[ \t]*\S", view.substr(line)):
                    prevline = line

            if row == lastrow:
                sel = sublime.Region(sel.begin(), prevline.end())
        return sel

    def _expand_block_julia(self, sel):
        view = self.view
        thiscmd = view.substr(view.line(sel))
        if (re.match(r"^\s*(?:function|if|for|while)", thiscmd) and
                not re.match(r".*end\s*$", thiscmd)) or \
                (re.match(r".*begin\s*$", thiscmd)):
            indentation = re.match("^(\s*)", thiscmd).group(1)
            end = view.find("^"+indentation+"end", sel.begin())
            sel = sublime.Region(sel.begin(), view.line(end.end()).end())

        return sel

    def expand_block(self, sel):
        syntax = self.get_syntax()
        if syntax == "r":
            esel = self._expand_block_r(sel)
        elif syntax == "python":
            esel = self._expand_block_python(sel)
        elif syntax == "julia":
            esel = self._expand_block_julia(sel)
        return esel


class SendTextPlusCommand(sublime_plugin.TextCommand,
                          SyntaxMixins,
                          SencTextMixins,
                          ExpandBlockMixins):
    def run(self, edit):
        view = self.view
        settings = self.syntax_settings()
        cmd = ''
        moved = False
        for sel in [s for s in view.sel()]:
            if sel.empty():
                esel = self.expand_block(sel)
                thiscmd = view.substr(view.line(esel))
                line = view.rowcol(esel.end())[0]
                if settings.get("auto_advance", False):
                    view.sel().subtract(sel)
                    pt = view.text_point(line+1, 0)
                    view.sel().add(sublime.Region(pt, pt))
                    moved = True
            else:
                thiscmd = view.substr(sel)
            cmd += thiscmd + '\n'

        if self.get_syntax() == "python":
            cmd = self.clean(cmd)
            if len(re.findall("\n", cmd)) > 0:
                cmd = "%cpaste\n" + cmd + "\n--"

        self.send_text(cmd)

        if moved:
            view.show(view.sel())


class SendTextPlusChangeDirCommand(sublime_plugin.TextCommand,
                                   SyntaxMixins,
                                   SencTextMixins):
    def run(self, edit):
        view = self.view
        fname = view.file_name()
        if not fname:
            sublime.error_message("Save the file!")
            return

        dirname = os.path.dirname(fname)
        syntax = self.get_syntax()

        if syntax == "r":
            cmd = "setwd(\"" + self.escape_dq(dirname) + "\")"
        elif syntax == "julia":
            cmd = "cd(\"" + self.escape_dq(dirname) + "\")"
        elif syntax == "python":
            cmd = "cd \"" + self.escape_dq(dirname) + "\""
        else:
            return

        self.send_text(cmd + "\n")


class SendTextPlusSourceCodeCommand(sublime_plugin.TextCommand,
                                    SyntaxMixins,
                                    SencTextMixins):
    def run(self, edit):
        view = self.view
        fname = view.file_name()
        if not fname:
            sublime.error_message("Save the file!")
            return

        syntax = self.get_syntax()

        if syntax == "r":
            cmd = "source(\"" + self.escape_dq(fname) + "\")"
        elif syntax == "julia":
            cmd = "include(\"" + self.escape_dq(fname) + "\")"
        elif syntax == "python":
            cmd = "%run \"" + self.escape_dq(fname) + "\""
        else:
            return

        self.send_text(cmd + "\n")
