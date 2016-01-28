; Get Cygwin window
WinGet, cygwin_id, ID, ahk_class mintty

; if not found, open cygwin
if (cygwin_id != "")
{
    Outputdebug % dstring . "id=" . cygwin_id

    oldclipboard = %clipboard%
    if 0 = 1
    {
        cmd = %1%
        cmd := RegExReplace(cmd, "^\n", "")
        newline = `n
        clipboard := cmd . newline
    }
    Else
    {
        clipboard = proc.time()`n
    }

    ControlSend, ,{Blind}+{Insert}, ahk_id %cygwin_id%
    clipboard := oldclipboard
}
