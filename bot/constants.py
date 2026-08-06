ENVIRONMENTS = ("development", "production")

MISSING_TOKEN = "DISCORD_TOKEN is not set"
INVALID_ENVIRONMENT = "ENVIRONMENT must be one of %s, got %r"
MISSING_DEV_GUILD_ID = "DEV_GUILD_ID is required when ENVIRONMENT=development"
NON_NUMERIC_DEV_GUILD_ID = "DEV_GUILD_ID must be numeric, got %r"
INVALID_MAX_POST_MB = "MAX_POST_MB must be a positive integer, got %r"
CONFIG_VALIDATED = "Configuration validated: environment=%s"

EXTRACTION_REQUESTED = "Extraction requested by %s for %s"
EXTRACTION_ERROR = "Extraction failed for %s"

COOKIES_LOADED = "Authenticating %s extraction with %s"
COOKIE_UNREADABLE = "Cookie file exists but cannot be read: %s"

SIZE_PROBE_FAILED = "Size probe (%s) failed for %s"
POST_SIZE_RESOLVED = "Post size resolved for %s: total=%s bytes, verdict=%s"
SIZING_ERROR = "Size resolution failed for %s"
POST_REFUSED = "Post refused for %s: verdict=%s, total=%s bytes, limit=%s bytes"
