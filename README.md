# UPET / Airrobo / Meowant Cat Litter Box for Home Assistant

Custom Home Assistant integration for UPET, Airrobo and Meowant self-cleaning litter boxes,
which all run on the same vendor cloud. It works with accounts from the UPET app (Europe and
Russia) and the AIR PET app (US and Canada), which Meowant boxes use.

This is a maintained fork of [CrazzyBerg/upet-hass](https://github.com/CrazzyBerg/upet-hass),
which did the original reverse engineering. The fork adds:

- **US and Canada accounts** from the AIR PET app.
- **Live updates** over one persistent MQTT connection: cat visits within seconds, a
  `Cat inside` sensor, and online status pushed by the box.
- **A visit log**: a Home Assistant event for every visit, presence change, box record, and
  undecoded vendor message, ready to keep long term.

The integration uses the vendor cloud API for account and device data, and the vendor IM/MQTT
channel for live updates and work commands.

| Box | Region | Tested |
| --- | --- | --- |
| Meowant MW-SC02 | US (AIR PET) | Everything, including live updates |
| UPET C10, C31 | EU (UPET) | Cloud data and commands, by upstream users. Live updates are untested on EU accounts; please report how they behave. |

## Warning

This is an unofficial integration and is not affiliated with, endorsed by, or supported by UPET, Airrobo, or the vendor.

Use it at your own risk. The integration depends on private vendor APIs and may stop working or trigger vendor-side account restrictions at any time. I am not responsible for blocked accounts, lost access, device issues, or any other consequences of using this integration.

For safer use, create a separate UPET/Airrobo account and share litter box access to that account instead of using your primary account.

## Features

- Account login with UPET/Airrobo credentials.
- Device discovery from the vendor cloud account.
- Read-only box, waste-bin, deodorant, online, and firmware data.
- Cat profile sensors and cat picture URL attributes when returned by the API.
- Config controls for confirmed settings:
  - Auto clean delay.
  - Auto clean on/off.
  - Deodorant alert.
  - Empty waste-bin reminder switch, time, and weekdays.
  - Do not disturb schedule.
  - Light schedule.
- MQTT work commands:
  - Start clean.
  - Pause clean.
  - Resume clean.
  - Flatten.
  - Pause flatten.
  - Resume flatten.
  - Raise litter rake.
  - Lower litter rake.
  - Request MQTT state.
- Live updates pushed by the box:
  - Cat inside (occupancy).
  - Online status.
  - Work mode.
  - Work state.
  - Work cause.
  - Last successful MQTT status update.
- Diagnostics download with sanitized raw API/coordinator data.
- Local brand icons for supported Home Assistant versions.

## Installation

Install through HACS as a custom repository:

1. Open HACS in Home Assistant.
2. Go to `Integrations`.
3. Open the three-dot menu and choose `Custom repositories`.
4. Add `https://github.com/bojanrajkovic/upet-hass`.
5. Select category `Integration`.
6. Install `UPET / Airrobo / Meowant Cat Litter Box`.

Coming from upstream? Remove the `CrazzyBerg/upet-hass` custom repository first. The
integration keeps the `ubpet` domain, so existing config entries carry over.

Restart Home Assistant after installation.

Manual installation is also possible by copying this repository's
`custom_components/ubpet` directory into your Home Assistant config directory:

```bash
<config>/custom_components/ubpet
```

Add the integration from Home Assistant:

```text
Settings -> Devices & services -> Add integration -> UPET / Airrobo / Meowant Cat Litter Box
```

## Configuration

Required fields:

- `Country`: the same country selected for the account in the official app.
- `Account`: UPET/Airrobo login account.
- `Password`: plain account password. The integration hashes it internally before sending it to the API.

The integration also needs vendor app credentials:

- `APP_ID`
- `APP_KEY`
- `PRODUCT`

Bundled app defaults are included with the integration, so normal setup asks
only for country, account, and password. The selected country chooses the vendor
region endpoint and is sent as the login area code. US and Canada accounts from
the AIR PET app (used by Meowant boxes) route to `apis.airrobo-home.com` with the
AIR PET app id, because that app keeps its own user pool. The app defaults are stored
in obfuscated form to keep raw values out of the repository.

If you maintain a private deployment and want to override the bundled app credentials,
use `custom_components/ubpet/secrets.py.example` as a template for a private
`secrets.py`.

## Entities

Device sensors:

- Box status.
- Empty waste-bin reminder days.
- Box use times.
- Waste-bin level.
- Waste-bin last reset.
- Box full max.
- Deodorant remaining days.
- Auto clean delay.
- Firmware version.
- Wi-Fi name.
- MQTT work mode.
- MQTT work state.
- MQTT work cause.
- Last REST update.
- Last MQTT update.

Device binary sensors:

- Cat inside. Taking the cover off jostles the scale, which the box reports as a cat, so
  scale readings don't count from the moment the cover comes off until the box is idle again.
- Cat nearby.
- Problems: cover open (the side cover on the MW-SC02), drum not in place, drum stuck
  (with the likely cause, as the app words it), scale fault, camera fault.
- Light.
- Firmware updating.
- Online.
- Deodorant expired.
- Sensor enabled.
- Camera enabled.

Device controls:

- Child lock, waste bin full alert, and shake mode (on boxes that support it) switches.
- Foreign object detection switch, on boxes that report the capability. The MW-SC02 doesn't.
- Waste bin full threshold number, up to the bin's capacity the box reports.
- Auto clean delay number.
- Auto clean switch.
- Deodorant alert switch.
- Empty waste-bin reminder switch.
- Empty waste-bin reminder time.
- Empty waste-bin reminder weekday select.
- Do not disturb switch and start/end times.
- Light schedule switch and start/end times.

Device buttons:

- REST request.
- MQTT request state.
- Reset waste-bin counter.
- Start clean.
- Pause clean.
- Resume clean.
- Flatten.
- Pause flatten.
- Resume flatten.
- Raise litter rake.
- Lower litter rake.

Cat sensors:

- Weight.
- Visits today.
- Time in box today.

The daily counters come from the same statistics the app shows, reset at local midnight, and
keep a daily sum in long-term statistics. The cat profile's own `number` and `costTime` fields
go stale and aren't used.

Cat picture URLs are exposed as cat entity attributes when returned by the vendor API.

Entities only appear for hardware the box has: camera entities need the
`cat_face_upload` capability (from `/catbox-server/box/config/device/capabilities`), the light
needs a `lightSwitch` in the box config, and the empty-waste-bin reminder needs a reminder
config. The rake buttons are disabled by default, because only UPET's open-tray boxes have a
rake and the API doesn't say which those are.

Re-pairing a box or recreating a cat profile gives it a new vendor id, so the old device stays
behind with dead entities. Delete it from the device page; the integration allows deleting any
box or cat the account no longer reports.

## Visit Log

When a box pushes a new record, or a cat steps out, the integration fetches
the records 3 seconds later. The 3-minute poll catches anything a push missed.
Each fetch reads the last 20 cat records per box. Every record newer than the
last one seen fires a `ubpet_visit` event and shows up in the Logbook as
"Hilda used Left Litter Box (3.3 kg, 59 s)". The `Last visit` sensor on each box
holds the newest visit, with the same fields as attributes.

Event data:

| Field | Meaning |
| --- | --- |
| `serial_number`, `box` | Which box |
| `record_id` | Vendor record id, unique and increasing |
| `cat_id`, `cat` | Identified cat, or `null` when the box couldn't tell |
| `weight_kg`, `duration_s` | Weight measured and time spent |
| `event_type` | Vendor code: `3` identified cat, `21` unidentified cat |
| `time` | Visit time, ISO 8601 UTC |
| `device_id`, `entity_id` | The cat's device (or the box's, for an unidentified cat) and the box's Cat inside sensor, so the visit shows on both device pages |

Box records, such as a finished cleaning cycle (`event_type` 31), fire
`ubpet_box_event` the same way, with the same fields. Their cat fields are
empty.

When a box reports a cat stepping in or out, the integration fires
`ubpet_presence` with `serial_number`, `box`, `inside` (true or false), and
`time`, the box's own timestamp. The `Cat inside` sensor follows the same
pushes.

Any MQTT message the integration doesn't recognize fires
`ubpet_unknown_message` with its raw bytes in `payload_hex`, plus the sender,
content type and RISP command when known. Command receipts are skipped. This
captures pushes nobody has decoded yet, such as health alerts.

The event reflects the cat known when the visit first appears. Assigning a
visit to a cat later in the app doesn't fire a new event.

The last reported record id is stored per box, so a restart neither drops nor
replays visits. Adding the integration doesn't replay past visits. More than 20
visits on one box between two fetches (a long outage) loses the oldest ones.

The recorder purges events after `purge_keep_days` (10 by default). To keep a
permanent CSV, point an automation at a [File](https://www.home-assistant.io/integrations/file/)
notify entity (`notify.litter_log` here):

```yaml
automation:
  - alias: Log litter box visits
    triggers:
      - trigger: event
        event_type: ubpet_visit
    actions:
      - action: notify.send_message
        target:
          entity_id: notify.litter_log
        data:
          message: >-
            {{ trigger.event.data.time }},{{ trigger.event.data.box }},
            {{ trigger.event.data.cat or 'unknown' }},{{ trigger.event.data.weight_kg }},
            {{ trigger.event.data.duration_s }}
```

## Live Updates

The integration holds one MQTT connection to the vendor broker
(`apis.airrobo-home.com:21000`, TLS) per account. The boxes push to every
account they're linked to:

| Push | What happens |
| --- | --- |
| Work state (RISP `0x400`) | Work mode, work state, box status, and Cat inside update at once. |
| New record (RISP `0x3ff`) | Visit records are fetched 3 seconds later. |
| Settings request (RISP `0x9e7`, 2535) | The box picked up a settings change, from the app, the box, or Home Assistant. Settings are fetched 3 seconds later. |
| Online status | The box's Online sensor updates at once. |

```mermaid
sequenceDiagram
  participant Box
  participant Broker as Vendor broker
  participant HA as Home Assistant
  participant API as Vendor REST API
  Box->>Broker: state: cat inside
  Broker->>HA: Cat inside = on
  Box->>Broker: state: cat left, new record
  Broker->>HA: Cat inside = off
  HA->>API: fetch last 20 records (3 s later)
  API-->>HA: visit
  HA->>HA: fire ubpet_visit
```

Commands go out over the same connection. After each connect, the integration
asks every box for its state, so the sensors fill in before anything happens.

### One session per account

The vendor allows one session per account. Any other login, such as the
mobile app or a second integration, takes over the session and disconnects
this one. The integration waits a minute before reconnecting, which signs the
other login out in turn. Each further takeover doubles the wait, up to 30
minutes, so occasional app use still works. A session that stays up for 10
minutes resets the wait.

While it waits, the integration also skips its REST polls, because any REST
login would sign the other session out early. When it reconnects, it fetches
the records it missed.

The integration's own token refresh also replaces the session, so in that
case it reconnects after 5 seconds.

To use the app and the integration side by side, share the boxes to a second
account and give the integration that one.

## Confirmed MQTT Commands

Current service ids and operation payload bodies:

| Service id | Meaning | Operation body |
| --- | --- | --- |
| `start_clean_up` | Start clean | `08011001` |
| `pause_clean_up` | Pause clean | `08011002` |
| `resume_clean_up` | Resume clean | `08011003` |
| `start_flatten` | Flatten / smoothing | `08031001` |
| `pause_flatten` | Pause flatten | `08031002` |
| `resume_flatten` | Resume flatten | `08031003` |
| `start_rise` | Raise litter rake | `08071001` |
| `start_drop` | Lower litter rake | `08081001` |

Confirmed operation ordinals:

- `CLEAN = 1`
- `SMOOTHING = 3`
- `RISE = 7`
- `DROP = 8`
- `START = 1`
- `PAUSE = 2`
- `RESUME = 3`

## Limitations

- The integration depends on the vendor cloud and vendor IM/MQTT service.
- One session per account: the mobile app and the integration disconnect each other. See [One session per account](#one-session-per-account).
- Commands aren't confirmed by their receipts. The state push that follows shows whether the box acted.
- Control board / child lock is currently exposed as read-only because the observed API flow returns a permission error for writes.
- Deodorize, direct light control, camera toggle, and full-alert threshold controls are not implemented yet.

## Development

Run dependency-free tests:

```bash
python3 -m unittest discover -s tests -v
```

Run quick checks:

```bash
python3 -m unittest tests.test_mqtt tests.test_api
python3 -m py_compile custom_components/ubpet/*.py
python3 -m json.tool custom_components/ubpet/strings.json >/tmp/ubpet_strings.json
python3 -m json.tool custom_components/ubpet/translations/en.json >/tmp/ubpet_en.json
python3 -m json.tool custom_components/ubpet/translations/uk.json >/tmp/ubpet_uk.json
```

The current tests cover:

- API signing and password hashing.
- Account type fallback.
- Authenticated request headers.
- Dashboard aggregation.
- Settings payload builders.
- IM credential/contact lookup.
- MQTT codec, RISP/protobuf payload generation, and service ordinals.
- Push classification, reconnect backoff, and presence changes.
- Diagnostics redaction.

## Implementation Notes

Implemented REST endpoints:

- `PUT /user-service-rest/v2/user/login`
- `GET /user-service-rest/v2/robot/common/device/list`
- `GET /catbox-server/box/config/allConfig?serialNumber=...`
- `GET /catbox-server/box/config/box-use-times/?serialNumber=...`
- `PUT /catbox-server/box/config/box-use-times/reset`
- `GET /catbox-server/app/deodorant-block/status?serialNumber=...`
- `GET /v1/ubtechinc-im-manager/im/online/device/?sn=...`
- `POST /v1/ubtechinc-im-manager/im/login`
- `GET /v1/ubtechinc-im-manager/im/friends`
- `GET /catbox-server/web/cat/info`
- `POST /catbox-server/web/box/record/new`
- `PUT /catbox-server/box/config/switch/update`
- `PUT /catbox-server/box/config/timePeriod/update`
- `PUT /catbox-server/box/config/timePoint/update`
- `POST /catbox-server/app/deodorant-block/switch`

MQTT command format:

```text
Message -> MessageContent(custom) -> Any(BytesValue) -> CommandProto(protype=2) -> RISP frame -> AirPet protobuf body
```

MQTT state request uses RISP command `0x3fd`. Operation commands use RISP command `0x3fb`. Boxes push work-state changes as `0x400`, with the same body as the `0x3fd` reply, and new-record signals as `0x3ff`.

## Roadmap

Planned or open work:

- Decode more MQTT receipt/error causes and surface command failures more clearly.
- Implement deodorize command if available.
- Implement full-alert threshold setting.
- Implement writable control board / child lock if a permitted API flow is found.
- Add Home Assistant platform tests with `pytest-homeassistant-custom-component`.

## Credits

The original integration, the UPET/Airrobo API client, and the MQTT command protocol are the
work of [@CrazzyBerg](https://github.com/CrazzyBerg) in
[CrazzyBerg/upet-hass](https://github.com/CrazzyBerg/upet-hass). This fork builds on it.
