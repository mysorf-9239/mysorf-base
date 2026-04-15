# Events

`mysorf_base.events` provides a minimal synchronous event bus for in-process
coordination.

It is intentionally small:

- `subscribe(event_name, handler)`
- `publish(event_name, payload=None)`
- optional `on_handler_error(event, handler, exc)` callback for caller-defined
  error policy

Special event name:

- `"*"` subscribes to every published event

Behavioral notes:

- publish is synchronous and in-process
- subscriber registration is thread-safe
- handler failures are suppressed and emitted as runtime warnings
- the bus does not replay historical events to subscribers added later

This is meant for lightweight integration points between infra and engine
layers, not for distributed messaging.
