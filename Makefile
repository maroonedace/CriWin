PYTHON ?= python3.12
PLATFORMS := youtube tiktok reddit instagram

# Which environment the cookie targets and `logs` act on.
# `make load-cookies ENV=development ...` points them at the development file.
ENV ?= production

# Compose interpolates ${COOKIE_DIR} from .env or the shell, never from the file
# handed to env_file. Reading it out of the active env file is what keeps the
# mount source, the path the bot reads, and the path load-cookies writes to from
# drifting into three different values.
read_cookie_dir = $(shell sed -n "s/^COOKIE_DIR=//p" $(1) 2>/dev/null | tr -d "\"'" | tail -n1)
cookie_dir = COOKIE_DIR="$(call read_cookie_dir,$(1))"

# The directory load-cookies and list-cookies operate on. Derived from the same
# env file the bot will read, so loading a cookie and finding it are the same
# path. Overridable on the command line for anything unusual.
COOKIE_DIR ?= $(or $(call read_cookie_dir,.env.$(ENV)),/mnt/criwin/cookies)


.PHONY: dev dev-down prod prod-down logs install-dev test load-cookies list-cookies

install-dev:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

test:
	.venv/bin/pytest

dev:
	ENV_FILE=.env.development $(call cookie_dir,.env.development) docker compose up --build -d

dev-down:
	ENV_FILE=.env.development $(call cookie_dir,.env.development) docker compose down

prod:
	ENV_FILE=.env.production $(call cookie_dir,.env.production) docker compose up --build -d

prod-down:
	ENV_FILE=.env.production $(call cookie_dir,.env.production) docker compose down

logs:
	ENV_FILE=.env.$(ENV) $(call cookie_dir,.env.$(ENV)) docker compose logs -f

load-cookies:
	@test -n "$(PLATFORM)" && test -n "$(FILE)" || { \
		echo "usage: make load-cookies PLATFORM=<name> FILE=/path/to/cookies.txt"; \
		echo "       platforms: $(PLATFORMS)"; exit 1; }
	@echo "$(PLATFORMS)" | tr ' ' '\n' | grep -qx -- "$(PLATFORM)" || { \
		echo "unknown platform '$(PLATFORM)'. one of: $(PLATFORMS)"; exit 1; }
	@test -f "$(FILE)" || { echo "no such file: $(FILE)"; \
		case "$(FILE)" in "~"*) \
			echo '       a leading ~ is not expanded in a make argument.';; \
		esac; exit 1; }
	@head -n1 "$(FILE)" | grep -q "Netscape HTTP Cookie File" || \
		echo "warning: $(FILE) does not look like a Netscape cookie export"
	install -D -m 0600 "$(FILE)" "$(COOKIE_DIR)/$(PLATFORM).txt"
	@echo "loaded $(PLATFORM) -> $(COOKIE_DIR)/$(PLATFORM).txt"

list-cookies:
	@ls -l "$(COOKIE_DIR)" 2>/dev/null || echo "no cookie directory at $(COOKIE_DIR)"
