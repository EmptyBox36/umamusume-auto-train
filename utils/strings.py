def clean_event_name(event_name):
  cleaned = event_name.replace("`", "'")  # apostrophe variations
  cleaned = " ".join(cleaned.split())  # multiple spaces
  return cleaned