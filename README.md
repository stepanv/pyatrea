# PyAtrea
Python library for communication with Atrea ventilation units

## Install:

```
python3 -m pip install pyatrea
```

## Usage examples:

### Initiate library:
```
from pyatrea import pyatrea

atrea = pyatrea.Atrea("192.168.0.2",80,"passwordOnAtreaWebsite")
```

### Get status of your unit with human readable identifications (if available):
```
status = atrea.getStatus()
if(status == False):
    exit("Authentication failed")

for id, value in status.items():
    print(atrea.getTranslation(id) + ":" + value)
```

### Get human readable warnings and errors:
```
status = atrea.getStatus()
params = atrea.getParams()

for warning in params['warning']:
    if status[warning] == "1":
        print(atrea.getTranslation(warning))
for alert in params['alert']:
    if status[alert] == "1":
        print(atrea.getTranslation(alert))
```

### Execute a one-shot register command:
This is intended for write-only registers which are not exposed in the unit's
parameter metadata. Register meanings remain the responsibility of the caller.

```
atrea.executeOneShotCommand(register_id, value)
```

### Command delivery

`exec()` consumes the currently queued batch. It detects rejected sessions,
including firmware that returns an HTTP 200 page containing `HTTP: 403 Forbidden`,
renews authentication, and retries that batch once. Other HTTP failures or
transport errors return `False`; requests have a 10-second timeout. A failed
batch is not kept for implicit replay by a later, unrelated action. Commands
queued while a batch is being sent remain available for the next call.
This does not make multi-caller queue preparation transactional, nor does an
HTTP success prove the unit has applied the requested setting; read back state.
