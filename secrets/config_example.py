### Eventbadge config file ###

# If you have a specific Eventbrite event you wish to use, enter its event ID below. (Can be found in the URL)
# Otherwise leave blank and Eventbadge will just choose the newest event.
eventbrite_event_id = ""

# Your Eventbrite API key - https://www.eventbrite.at/account-settings/apps
eventbrite_key = ""

# How frequent to poll Eventbrite. Be careful you don't hit the rate limit! In seconds.
delay_between_eventbrite_queries = 10


# If using with NIJIS (https://github.com/gbaman/NI-Jam-Information-System), set the below to True.
use_nijis = False

# The base URL for your instance of NIJIS. For example https://example.com
nijis_base_url = ""

# NIJIS API key to allow Eventbadge to grab the day password.
nijis_api_key = ""