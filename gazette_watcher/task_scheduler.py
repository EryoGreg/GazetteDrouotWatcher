"""
Native Windows Task Scheduler control, via the Task Scheduler COM API
(no PowerShell, no shelling out to schtasks.exe).

Registering a task this way, under TASK_LOGON_INTERACTIVE_TOKEN (i.e. "run
only when this user is logged on, using their own session"), does not
require administrator rights for a user managing their own task — this is
also what sidesteps the intermittent "Access is denied" seen earlier from
PowerShell's Register-ScheduledTask/Enable-ScheduledTask cmdlets, in every
context except one: some restricted/non-interactive process tokens (e.g.
certain automation/remote-execution contexts) genuinely lack the privilege
regardless of method — that's a property of the calling process's session,
not something either this module or PowerShell can work around.

A trigger's Repetition.Duration left as an empty string means "repeat
forever" in this API — simpler than the PowerShell equivalent, which
can't represent "forever" directly and needed a 10-year duration as a
stand-in.
"""

import datetime
import functools
import os

import win32com.client

TASK_NAME = "GazetteDrouotWatcher"

_TASK_ACTION_EXEC = 0
_TASK_TRIGGER_TIME = 1
_TASK_LOGON_INTERACTIVE_TOKEN = 3
_TASK_CREATE_OR_UPDATE = 6
_TASK_INSTANCES_IGNORE_NEW = 3

_STATE_NAMES = {0: "unknown", 1: "disabled", 2: "queued", 3: "ready", 4: "running"}

# 0x80070005 (E_ACCESSDENIED) as a signed 32-bit int — how it shows up in a
# pywintypes.com_error's message/args.
_ACCESS_DENIED_HRESULT = -2147024891


class TaskNotInstalledError(Exception):
    """Raised when an operation needs the task to already be registered, but it isn't."""


class PermissionDeniedError(Exception):
    """Raised when Windows denies the underlying COM call — see the module
    docstring for why this can happen even for a user's own interactive task."""


def _translate_errors(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except TaskNotInstalledError:
            raise
        except Exception as e:
            if str(_ACCESS_DENIED_HRESULT) in str(e):
                raise PermissionDeniedError(str(e)) from e
            raise

    return wrapper


def _connect():
    scheduler = win32com.client.Dispatch("Schedule.Service")
    scheduler.Connect()
    return scheduler


def _root_folder():
    return _connect().GetFolder("\\")


def _get_task_or_raise(root_folder):
    try:
        return root_folder.GetTask(TASK_NAME)
    except Exception as e:
        raise TaskNotInstalledError(str(e)) from e


@_translate_errors
def install_task(exe_path: str, arguments: str, working_dir: str, interval_minutes: int):
    """Registers (or re-registers, overwriting) the task: runs `exe_path
    arguments` once right away, then every interval_minutes indefinitely
    after that — only while the installing user is logged in.

    A time trigger with StartBoundary set in the past (so it's already
    "due" by the time registration completes) rather than a logon trigger
    — a logon trigger only fires on the *next* logon, so installing (or a
    Settings Save that re-registers this with a changed interval)
    wouldn't actually run anything until the next time the user signed
    in, which reads as the app doing nothing right after you set it up.
    This runs once immediately instead, then keeps repeating exactly like
    the logon trigger did.

    "Immediately" here doesn't rely on Task Scheduler's own due-trigger
    polling to notice a just-registered task fast enough (its engine only
    sweeps for due triggers periodically, and testing showed a task could
    still be sitting at "never run" a couple of minutes after install) —
    the explicit task.Run(None) below kicks off that first run directly
    and deterministically, independent of any of that polling timing.
    The past StartBoundary is kept anyway so the *ongoing* repetition
    pattern's reference point is unambiguous.

    Passing userId="" to RegisterTaskDefinition below resolves to the
    calling (installing) user, so this always runs as that one specific
    user's session regardless of who else logs into the machine — a time
    trigger has no logon-scoping concept to begin with, unlike the old
    logon trigger, which Task Scheduler's UI displayed as "At log on of
    any user" even though it could only ever actually run as this one."""
    scheduler = _connect()
    root_folder = scheduler.GetFolder("\\")
    task_def = scheduler.NewTask(0)

    task_def.RegistrationInfo.Description = "Gazette Drouot Watcher — periodic check for new articles"
    # Neither of these gets auto-filled by RegisterTaskDefinition the way
    # the Task Scheduler UI would fill them in for a task created there
    # directly -- left unset, both show up blank in Task Scheduler.
    task_def.RegistrationInfo.Author = f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}"
    task_def.RegistrationInfo.Date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    task_def.Settings.Enabled = True
    task_def.Settings.StartWhenAvailable = True
    task_def.Settings.DisallowStartIfOnBatteries = False
    task_def.Settings.StopIfGoingOnBatteries = False
    task_def.Settings.MultipleInstances = _TASK_INSTANCES_IGNORE_NEW
    task_def.Settings.ExecutionTimeLimit = "PT5M"

    trigger = task_def.Triggers.Create(_TASK_TRIGGER_TIME)
    trigger.Id = "TimeTriggerRepeat"
    # 5 seconds wasn't enough of a margin -- StartBoundary's whole-second
    # truncation plus how long RegisterTaskDefinition itself takes to
    # complete could still land it in the future by the time the task is
    # actually live, especially on a slower machine, so Task Scheduler
    # never saw a "due" first run to catch up on. 90 seconds gives it
    # comfortable room regardless of machine speed.
    start = datetime.datetime.now() - datetime.timedelta(seconds=90)
    trigger.StartBoundary = start.strftime("%Y-%m-%dT%H:%M:%S")
    trigger.Repetition.Interval = f"PT{interval_minutes}M"
    trigger.Repetition.Duration = ""  # empty = repeat forever
    trigger.Repetition.StopAtDurationEnd = False

    action = task_def.Actions.Create(_TASK_ACTION_EXEC)
    action.Path = exe_path
    action.Arguments = arguments
    action.WorkingDirectory = working_dir

    task_def.Principal.LogonType = _TASK_LOGON_INTERACTIVE_TOKEN

    registered_task = root_folder.RegisterTaskDefinition(
        TASK_NAME, task_def, _TASK_CREATE_OR_UPDATE, "", "", _TASK_LOGON_INTERACTIVE_TOKEN
    )
    try:
        registered_task.Run(None)
    except Exception:
        # The task is validly registered either way and will still run on
        # its own schedule -- this is just a best-effort kick for instant
        # feedback, not something that should make install_task() itself
        # report failure.
        pass


@_translate_errors
def uninstall_task():
    """No-op (not an error) if the task isn't currently registered — but a
    real failure to delete an EXISTING task (e.g. access denied) must not
    be swallowed the same way, or the caller wrongly believes it worked."""
    root_folder = _root_folder()
    try:
        root_folder.GetTask(TASK_NAME)
    except Exception:
        return  # not installed, nothing to do
    root_folder.DeleteTask(TASK_NAME, 0)


def get_task_status() -> str:
    """Returns "not_installed", or one of _STATE_NAMES' values
    ("ready", "disabled", "running", "queued", "unknown"). Never raises —
    this is used for a passive status display, not an action."""
    try:
        root_folder = _root_folder()
        task = root_folder.GetTask(TASK_NAME)
    except Exception:
        return "not_installed"
    return _STATE_NAMES.get(task.State, "unknown")


@_translate_errors
def set_enabled(enabled: bool):
    root_folder = _root_folder()
    task = _get_task_or_raise(root_folder)
    task.Enabled = enabled


@_translate_errors
def run_now():
    root_folder = _root_folder()
    task = _get_task_or_raise(root_folder)
    task.Run(None)
