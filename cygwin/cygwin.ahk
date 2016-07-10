; Get Cygwin window
WinGet, cygwin_id, ID, ahk_class mintty

; if not found, open cygwin
if (cygwin_id != "")
{
    ControlSend, ,{Blind}+{Insert}, ahk_id %cygwin_id%
}
