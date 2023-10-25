from dataclasses import dataclass

import pendulum as pd


@dataclass
class Event:
    start: pd.Time
    end: pd.Time
    day: pd.Date
