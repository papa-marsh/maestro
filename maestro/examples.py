from structlog.stdlib import get_logger

from maestro.integrations import NotifActionEvent, StateChangeEvent
from maestro.registry import switch
from maestro.triggers import (
    cron_trigger,
    event_fired_trigger,
    notif_action_trigger,
    state_change_trigger,
)

log = get_logger()

# TODO: Write up some examples
