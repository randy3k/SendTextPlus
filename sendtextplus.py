import sublime
import sublime_plugin
import os
import subprocess
import re

class SendTextPlusCommand(sublime_plugin.TextCommand):
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

    def run(self, edit, prog, cmd):
        settings = sublime.load_settings("SendTextPlus.sublime-settings")
        plat = sublime.platform()
        if plat == 'osx':
            if prog == 'Terminal':
                cmd = self.clean(cmd)
                cmd = self.escape_dq(cmd)
                args = ['osascript']
                args.extend(['-e', 'tell app "Terminal" to do script "' + cmd + '" in front window\n'])
                subprocess.Popen(args)

            elif prog == "iTerm":
                cmd = self.clean(cmd)
                cmd = self.escape_dq(cmd)
                # when cmd ends in a space, iterm does not execute. Thus append a line break.
                if (cmd[-1:] == ' '):
                    cmd += '\n'
                args = ['osascript']
                args.extend(['-e', 'tell app "iTerm" to tell the first terminal to tell current session to write text "' + cmd +'"'])
                subprocess.Popen(args)

        if plat == 'linux':
            if prog == "tmux":
                progpath = settings.get("tmux", "tmux")
                subprocess.call([progpath, 'set-buffer', cmd + "\n"])
                subprocess.call([progpath, 'paste-buffer', '-d'])

            elif prog == "screen":
                progpath = settings.get("screen", "screen")
                subprocess.call([progpath, '-X', 'stuff', cmd + "\n"])

        elif plat == 'windows':
            raise Exception("not yet supported")
