import argparse
from datetime import datetime, timezone
from calendar import monthrange
from typing import Tuple, Optional
from zoneinfo import ZoneInfo

def format_as_zulu(dt: datetime) -> str:
    """
    Format a datetime object as ISO format with 'Z' timezone indicator.
    
    Args:
        dt (datetime): Datetime object in UTC
        
    Returns:
        str: ISO format string with 'Z' timezone
    """
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def generate_date_range(year: int, start_month: int, end_month: Optional[int] = None) -> Tuple[str, str]:
    """
    Generate ISO format datetime strings for the start and end of a month or month range.
    
    Args:
        year (int): Valid year
        start_month (int): Starting month (1-12)
        end_month (Optional[int]): Optional ending month (1-12)
    
    Returns:
        Tuple[str, str]: Tuple containing start and end datetime strings in ISO format with Z timezone
        
    Raises:
        ValueError: If invalid year or month parameters are provided
    """
    # Validate year
    if not isinstance(year, int) or year < 1:
        raise ValueError("Year must be a positive integer")
    
    # Validate months
    if not isinstance(start_month, int) or start_month < 1 or start_month > 12:
        raise ValueError("Start month must be an integer between 1 and 12")
    
    if end_month is not None:
        if not isinstance(end_month, int) or end_month < 1 or end_month > 12:
            raise ValueError("End month must be an integer between 1 and 12")
        if end_month < start_month:
            raise ValueError("End month cannot be before start month")
    
    # Calculate start datetime (first minute of start_month)
    start_dt = datetime(year, start_month, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    # Calculate end datetime (last minute of end_month or start_month if end_month not provided)
    target_month = end_month if end_month is not None else start_month
    _, last_day = monthrange(year, target_month)
    end_dt = datetime(year, target_month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    
    return format_as_zulu(start_dt), format_as_zulu(end_dt)

def convert_luxembourg_to_utc(datetime_strings: list[str]) -> list[str]:
    """
    Convert datetime strings from Europe/Luxembourg timezone to UTC/Zulu.
    Handles daylight saving time automatically.
    
    Args:
        datetime_strings (list[str]): List of ISO format datetime strings in Luxembourg timezone
        
    Returns:
        list[str]: List of ISO format datetime strings in UTC with Z timezone indicator
        
    Raises:
        ValueError: If datetime strings are not in valid ISO format
    """
    luxembourg_tz = ZoneInfo("Europe/Luxembourg")
    converted_dates = []
    
    for dt_string in datetime_strings:
        try:
            # Parse the input datetime string
            # If the string already has timezone info, it will be preserved
            local_dt = datetime.fromisoformat(dt_string)
            
            # If the datetime is naive (no timezone), assume it's Luxembourg time
            if local_dt.tzinfo is None:
                local_dt = local_dt.replace(tzinfo=luxembourg_tz)
            elif local_dt.tzinfo != luxembourg_tz:
                # If it has a different timezone, convert it to Luxembourg first
                local_dt = local_dt.astimezone(luxembourg_tz)
            
            # Convert to UTC and format with Z
            utc_dt = local_dt.astimezone(timezone.utc)
            converted_dates.append(format_as_zulu(utc_dt))
            
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {dt_string}. Error: {str(e)}")
    
    return converted_dates
