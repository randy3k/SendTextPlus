import sublime
import sublime_plugin
import os
import re
import subprocess


def sget(key, default=None):
    s = sublime.load_settings("SendText+.sublime-settings")
    return s.get(key, default)


def get_program(view):
    plat = sublime.platform()
    prog = sget("prog")
    if prog:
        return prog
    defaults = sget("defaults")
    pt = view.sel()[0].begin() if len(view.sel()) > 0 else 0

    for d in defaults:
        match_platform = plat == d.get("platform", plat)
        scopes = d.get("scopes", None)
        match_scopes = not scopes or any([view.score_selector(pt, s) > 0 for s in scopes])
        if match_platform and match_scopes and "prog" in d:
            return d.get("prog")
    return None


class TextSender:

    def __init__(self, view):
        self.view = view
        plat = sublime.platform()
        prog = get_program(view)
        function_str = "_dispatch_" + prog.lower().replace("-", "_")
        if getattr(self, function_str + "_" + plat, None):
            function_str = function_str + "_" + plat
        self.send_text = eval("self." + function_str)

    @classmethod
    def init(cls, view):
        return cls(view)

    @staticmethod
    def clean_cmd(cmd):
        cmd = cmd.expandtabs(4)
        cmd = cmd.rstrip('\n')
        if len(re.findall("\n", cmd)) == 0:
            cmd = cmd.lstrip()
        return cmd

    @staticmethod
    def escape_dquote(cmd):
        cmd = cmd.replace('\\', '\\\\')
        cmd = cmd.replace('"', '\\"')
        return cmd

    def _dispatch_terminal(self, cmd):
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        args = ['osascript']
        args.extend(['-e',
                     'tell application "Terminal" to do script "' + cmd + '" in front window'])
        subprocess.Popen(args)

    @staticmethod
    def iterm_version():
        args = ['osascript', '-e', 'tell application "iTerm" to get version']
        ver = subprocess.check_output(args).decode().strip()
        return tuple((int(i) for i in re.split(r"\.", ver)[0:2]))

    def _dispatch_iterm(self, cmd):
        cmd = self.clean_cmd(cmd)
        if self.iterm_version() >= (2, 9):
            n = 1000
            chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
            for chunk in chunks:
                subprocess.call([
                    'osascript', '-e',
                    'tell application "iTerm" to tell the current window ' +
                    'to tell current session to write text "' +
                    self.escape_dquote(chunk) + '" without newline'
                ])
            subprocess.call([
                'osascript', '-e',
                'tell application "iTerm" to tell the current window ' +
                'to tell current session to write text ""'
            ])
        else:
            subprocess.call([
                'osascript', '-e',
                'tell application "iTerm" to tell the current terminal ' +
                'to tell current session to write text "' +
                self.escape_dquote(cmd) + '"'
            ])

    def _dispatch_r_osx(self, cmd):
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        args = ['osascript']
        args.extend(['-e', 'tell application "R" to cmd "' + cmd + '"'])
        subprocess.Popen(args)

    def _dispatch_rstudio_osx(self, cmd):
        cmd = self.clean_cmd(cmd)
        script = """
        on run argv
            tell application "RStudio"
                cmd item 1 of argv
            end tell
        end run
        """
        subprocess.call(['osascript', '-e', script, cmd])

    def _dispatch_chrome_rstudio(self, cmd):
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        cmd = cmd.replace("\n", r"\n")
        # use window.desktopHooks.evaluateRCmd once
        # https://github.com/rstudio/rstudio/commit/3c11a669e7eaae0af40b935fb22cf1bf0e7d6b73
        # is released.
        script = """
        on run argv
            tell application "Google Chrome"
                set URL of front window's active tab to "javascript:{" & "
                    var input = document.getElementById('rstudio_console_input');
                    var textarea = input.getElementsByTagName('textarea')[0];
                    textarea.value += \\"" & item 1 of argv & "\\";
                    var e = document.createEvent('KeyboardEvent');
                    e.initKeyboardEvent('input');
                    textarea.dispatchEvent(e);
                    var e = document.createEvent('KeyboardEvent');
                    e.initKeyboardEvent('keydown');
                    Object.defineProperty(e, 'keyCode', {'value' : 13});
                    input.dispatchEvent(e);
                " & "}"
            end tell
        end run
        """
        subprocess.call(['osascript', '-e', script, cmd])

    def _dispatch_safari_rstudio(self, cmd):
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        cmd = cmd.replace("\n", r"\n")
        script = """
        on run argv
            tell application "Safari"
                tell front window's current tab to do JavaScript "
                    var input = document.getElementById('rstudio_console_input');
                    var textarea = input.getElementsByTagName('textarea')[0];
                    textarea.value += \\"" & item 1 of argv & "\\";
                    var e = document.createEvent('KeyboardEvent');
                    e.initKeyboardEvent('input');
                    textarea.dispatchEvent(e);
                    var e = document.createEvent('KeyboardEvent');
                    e.initKeyboardEvent('keydown');
                    Object.defineProperty(e, 'keyCode', {'value' : 13});
                    input.dispatchEvent(e);
                "
            end tell
        end run
        """
        subprocess.call(['osascript', '-e', script, cmd])

    def _dispatch_chrome_jupyter(self, cmd):
        # remove possible ipython code block
        cmd = re.sub(r"%cpaste\n(.*)\n--", r"\1", cmd, flags=re.S)
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        cmd = cmd.replace("\n", r"\n")
        script = """
        on run argv
            tell application "Google Chrome"
                set URL of front window's active tab to "javascript:{" & "
                    var mycell = IPython.notebook.get_selected_cell();
                    mycell.set_text(\\"" & item 1 of argv & "\\");
                    mycell.execute();
                    var nextcell = IPython.notebook.insert_cell_below();
                    IPython.notebook.select_next();
                    IPython.notebook.scroll_to_cell(IPython.notebook.find_cell_index(nextcell));
                " & "}"
            end tell
        end run
        """
        subprocess.call(['osascript', '-e', script, cmd])

    def _dispatch_safari_jupyter(self, cmd):
        # remove possible ipython code block
        cmd = re.sub(r"%cpaste\n(.*)\n--", r"\1", cmd, flags=re.S)
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        cmd = cmd.replace("\n", r"\n")
        script = """
        on run argv
            tell application "Safari"
                tell front window's current tab to do JavaScript "
                    var mycell = IPython.notebook.get_selected_cell();
                    mycell.set_text(\\"" & item 1 of argv & "\\");
                    mycell.execute();
                    var nextcell = IPython.notebook.insert_cell_below();
                    IPython.notebook.select_next();
                    IPython.notebook.scroll_to_cell(IPython.notebook.find_cell_index(nextcell));
                "
            end tell
        end run
        """
        subprocess.call(['osascript', '-e', script, cmd])

    def _dispatch_tmux(self, cmd):
        tmux = sget("tmux", "tmux")
        cmd = self.clean_cmd(cmd) + "\n"
        n = 200
        chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
        for chunk in chunks:
            subprocess.call([tmux, 'set-buffer', chunk])
            subprocess.call([tmux, 'paste-buffer', '-d'])

    def _dispatch_screen(self, cmd):
        screen = sget("screen", "screen")
        plat = sublime.platform()
        cmd = self.clean_cmd(cmd) + "\n"
        n = 200
        chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
        for chunk in chunks:
            if plat == "linux":
                chunk = chunk.replace("\\", r"\\")
                chunk = chunk.replace("$", r"\$")
            subprocess.call([screen, '-X', 'stuff', chunk])

    @staticmethod
    def execute_ahk_script(script, cmd, args=[]):
        ahk_path = os.path.join(sublime.packages_path(),
                                'User', 'SendText+', 'bin', 'AutoHotkeyU32')
        ahk_script_path = os.path.join(sublime.packages_path(),
                                       'User', 'SendText+', 'bin', script)
        # manually add "\n" to keep the indentation of first line of block code,
        # "\n" is later removed in AutoHotkey script
        cmd = "\n" + cmd
        subprocess.Popen([ahk_path, ahk_script_path, cmd] + args)

    def _dispatch_cygwin(self, cmd):
        cmd = self.clean_cmd(cmd)
        self.execute_ahk_script("Cygwin.ahk", cmd)

    def _dispatch_cmder(self, cmd):
        cmd = self.clean_cmd(cmd)
        self.execute_ahk_script("Cmder.ahk", cmd)

    def _dispatch_r32_windows(self, cmd):
        cmd = self.clean_cmd(cmd)
        self.execute_ahk_script("Rgui.ahk", cmd, [sget("R32", "0")])

    def _dispatch_r64_windows(self, cmd):
        cmd = self.clean_cmd(cmd)
        self.execute_ahk_script("Rgui.ahk", cmd, [sget("R64", "1")])

    def _dispatch_rstudio_windows(self, cmd):
        cmd = self.clean_cmd(cmd)
        self.execute_ahk_script("RStudio.ahk", cmd)

    def _dispatch_sublimerepl(self, cmd):
        cmd = self.clean_cmd(cmd)
        window = sublime.active_window()
        view = window.active_view()
        external_id = view.scope_name(0).split(" ")[0].split(".", 1)[1]
        window.run_command(
            "repl_send", {"external_id": external_id, "text": cmd})


class TextGetter:

    def __init__(self, view):
        self.view = view

    @classmethod
    def init(cls, view):
        pt = view.sel()[0].begin() if len(view.sel()) > 0 else 0
        if view.score_selector(pt, "source.r"):
            getter = RTextGetter(view)
        elif view.score_selector(pt, "source.python"):
            getter = PythonTextGetter(view)
        elif view.score_selector(pt, "source.julia"):
            getter = JuliaTextGetter(view)
        else:
            getter = cls(view)

        return getter

    def expand_line(self, s):
        return self.view.line(s)

    def advance(self, s):
        view = self.view
        view.sel().subtract(s)
        pt = view.text_point(view.rowcol(s.end())[0]+1, 0)
        if sget("auto_advance_non_empty", False):
            nextpt = view.find(r"\S", pt)
            if nextpt.begin() != -1:
                pt = view.text_point(view.rowcol(nextpt.begin())[0], 0)
        view.sel().add(sublime.Region(pt, pt))

    def get_text(self):
        view = self.view
        cmd = ''
        moved = False
        for s in [s for s in view.sel()]:
            if s.empty():
                s = self.expand_line(s)
                if sget("auto_advance", True):
                    self.advance(s)
                    moved = True

            cmd += view.substr(s) + '\n'

        if moved:
            view.show(view.sel())

        return cmd


class RTextGetter(TextGetter):

    def expand_line(self, s):
        view = self.view
        # expand selection to {...}
        s = view.line(s)
        thiscmd = view.substr(s)
        if re.match(r".*\{\s*$", thiscmd):
            es = view.find(
                r"""^(?:.*(\{(?:(["\'])(?:[^\\]|\\.)*?\2|#.*$|[^\{\}]|(?1))*\})[^\{\}\n]*)+""",
                view.line(s).begin()
            )
            if s.begin() == es.begin():
                s = es
        return s


class PythonTextGetter(TextGetter):

    def expand_line(self, s):
        view = self.view
        s = view.line(s)
        thiscmd = view.substr(s)
        row = view.rowcol(s.begin())[0]
        prevline = view.line(s.begin())
        lastrow = view.rowcol(view.size())[0]
        if re.match(r"^(#\s%%|#%%|# In\[)", thiscmd):
            while row < lastrow:
                row = row + 1
                line = view.line(view.text_point(row, 0))
                m = re.match(r"^(#\s%%|#%%|# In\[)", view.substr(line))
                if m:
                    s = sublime.Region(s.begin(), prevline.end())
                    break
                else:
                    prevline = line

        elif re.match(r"^[ \t]*\S", thiscmd):
            indentation = re.match(r"^([ \t]*)", thiscmd).group(1)
            while row < lastrow:
                row = row + 1
                line = view.line(view.text_point(row, 0))
                m = re.match(r"^([ \t]*)([^\n\s]+)", view.substr(line))
                if m and len(m.group(1)) <= len(indentation) and \
                        (len(m.group(1)) < len(indentation) or
                            not re.match(r"else|elif|except|finally", m.group(2))):
                    s = sublime.Region(s.begin(), prevline.end())
                    break
                elif re.match(r"^[ \t]*\S", view.substr(line)):
                    prevline = line

        if row == lastrow:
            s = sublime.Region(s.begin(), prevline.end())
        return s

    def get_text(self):
        cmd = super(PythonTextGetter, self).get_text()
        cmd = cmd.rstrip("\n")
        if len(re.findall("\n", cmd)) > 0:
            cmd = "%cpaste -q\n" + cmd + "\n--"
        return cmd


class JuliaTextGetter(TextGetter):

    def expand_line(self, s):
        view = self.view
        s = view.line(s)
        thiscmd = view.substr(s)
        if (re.match(r"^\s*(?:function|if|for|while)", thiscmd) and
                not re.match(r".*end\s*$", thiscmd)) or \
                (re.match(r".*begin\s*$", thiscmd)):
            indentation = re.match("^(\s*)", thiscmd).group(1)
            end = view.find("^"+indentation+"end", s.begin())
            s = sublime.Region(s.begin(), view.line(end.end()).end())

        return s


class SendTextPlusCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        getter = TextGetter.init(view)
        cmd = getter.get_text()
        sender = TextSender.init(view)
        sender.send_text(cmd)


class SendTextPlusChangeDirCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        fname = view.file_name()
        if not fname:
            sublime.error_message("Save the file!")
            return

        dirname = os.path.dirname(fname)

        sender = TextSender.init(view)

        pt = view.sel()[0].begin() if len(view.sel()) > 0 else 0
        if view.score_selector(pt, "source.r"):
            cmd = "setwd(\"" + sender.escape_dquote(dirname) + "\")"
        elif view.score_selector(pt, "source.python"):
            cmd = "cd \"" + sender.escape_dquote(dirname) + "\""
        elif view.score_selector(pt, "source.julia"):
            cmd = "cd(\"" + sender.escape_dquote(dirname) + "\")"

        sender.send_text(cmd+"\n")


class SendTextPlusSourceCodeCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        fname = view.file_name()
        if not fname:
            sublime.error_message("Save the file!")
            return

        sender = TextSender.init(view)

        pt = view.sel()[0].begin() if len(view.sel()) > 0 else 0
        if view.score_selector(pt, "source.r"):
            cmd = "source(\"" + sender.escape_dquote(fname) + "\")"
        elif view.score_selector(pt, "source.python"):
            cmd = "%run \"" + sender.escape_dquote(fname) + "\""
        elif view.score_selector(pt, "source.julia"):
            cmd = "include(\"" + sender.escape_dquote(fname) + "\")"

        sender.send_text(cmd+"\n")


class SendTextPlusBuildCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.window.active_view().run_command("send_text_plus_source_code")


class SendTextPlusChooseProgramCommand(sublime_plugin.WindowCommand):

    def show_quick_panel(self, options, done):
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done), 10)

    def run(self):
        plat = sublime.platform()
        if plat == 'osx':
            self.app_list = ["[Defaults]", "Terminal", "iTerm",
                             "R", "RStudio", "Chrome-RStudio", "Chrome-Jupyter",
                             "Safari-RStudio", "Safari-Jupyter",
                             "tmux", "screen", "SublimeREPL"]
        elif plat == "windows":
            self.app_list = ["[Defaults]", "Cmder", "Cygwin",
                             "R32", "R64", "RStudio", "SublimeREPL"]
        elif plat == "linux":
            self.app_list = ["[Defaults]", "tmux", "screen", "SublimeREPL"]
        else:
            sublime.error_message("Platform not supported!")

        self.show_quick_panel(self.app_list, self.on_done)

    def on_done(self, action):
        if action == -1:
            return
        settings = sublime.load_settings('SendText+.sublime-settings')
        settings.set("prog", self.app_list[action] if action > 0 else None)
        sublime.save_settings('SendText+.sublime-settings')
