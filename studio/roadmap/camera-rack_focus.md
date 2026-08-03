# rack_focus (camera)

Accepted by the format, not yet renderable. Falls back to `static`.

**Blocked because** a single flat generated image has no depth information to refocus or
orbit around.

**Path:** the same depth-estimation route as `dolly_zoom` (Depth Anything 3 is installed)
— estimate depth, then blur by depth for rack focus, or displace by depth for a short orbit.
Rack focus is the more achievable of the two and the more useful: shifting attention within
a frame without cutting is a basic tool we currently cannot reach for.
