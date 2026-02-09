from contextvars import ContextVar

# Context variable to hold the current user_id for tools
current_user_id: ContextVar[str] = ContextVar("current_user_id", default="")
# Context variable to hold the current radar_id for tools during sync
current_radar_id: ContextVar[str] = ContextVar("current_radar_id", default="")
