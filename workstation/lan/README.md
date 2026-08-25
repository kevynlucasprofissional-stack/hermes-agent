# LAN / mobile control plane

Workstation LAN must reuse the official Hermes Dashboard and its authentication
gate. Never start an independent Workstation web server for chat/tasks/state.

V1 implementation target:
1. auth provider configured
2. bind official dashboard to `0.0.0.0:9119`
3. detect LAN IPv4
4. show authenticated URL + QR in Desktop
5. expose Workstation browser-task event stream through the same Hermes backend

Hard invariant: non-loopback bind without authentication is rejected.
Tailscale is V1.1.
