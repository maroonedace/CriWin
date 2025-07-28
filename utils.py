import re

# 1. A regex to match youtu.be/<ID> or youtube.com/watch?v=<ID>
YOUTUBE_REGEX = re.compile(
    r'^(https?://)?'                                 # optional scheme
    r'((www\.)?youtu\.be/|((m|www)\.)?youtube\.com/)' # domain
    r'((watch\?v=)|embed/|v/)?'                       # optional path prefixes
    r'(?P<id>[\w-]{11})'                              # video ID
    r'([&?].*)?$'                                     # optional extra params
)

def is_valid_youtube_url(url: str) -> bool:
    match = YOUTUBE_REGEX.match(url)
    return bool(match)