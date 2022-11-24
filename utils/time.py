import re
import datetime
from typing import Optional, List, SupportsInt
from .format import plural, human_join
from datetime import timedelta
from discord.ext import commands
from dateutil.relativedelta import relativedelta
import discord
import parsedatetime as pdt
from utils.errors import ArgumentBaseError


TIME_RE_STRING = r"\s?".join(
    [
        r"((?P<weeks>\d+?)\s?(weeks?|w))?",                  # e.g. 2w
        r"((?P<days>\d+?)\s?(days?|d))?",                    # e.g. 4d
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))?",            # e.g. 10h
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m(?!o)))?",   # e.g. 20m
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))?",        # e.g. 30s
    ]
)

TIME_RE = re.compile(TIME_RE_STRING, re.I)

class ShortTime:
    compiled = re.compile("""(?:(?P<years>[0-9])(?:years?|y))?             # e.g. 2y
                             (?:(?P<months>[0-9]{1,2})(?:months?|mo))?     # e.g. 2months
                             (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?        # e.g. 10w
                             (?:(?P<days>[0-9]{1,5})(?:days?|d))?          # e.g. 14d
                             (?:(?P<hours>[0-9]{1,5})(?:hours?|h))?        # e.g. 12h
                             (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m))?    # e.g. 10m
                             (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s))?    # e.g. 15s
                          """, re.VERBOSE)

    def __init__(self, argument, *, now=None):
        match = self.compiled.fullmatch(argument)
        if match is None or not match.group(0):
            raise commands.BadArgument('invalid time provided')

        data = { k: int(v) for k, v in match.groupdict(default=0).items() }
        now = now or datetime.datetime.now(datetime.timezone.utc)
        self.dt = now + relativedelta(**data)

    @classmethod
    async def convert(cls, ctx, argument):
        return cls(argument, now=ctx.message.created_at)

class HumanTime:
    calendar = pdt.Calendar(version=pdt.VERSION_CONTEXT_STYLE)

    def __init__(self, argument, *, now=None):
        now = now or datetime.datetime.utcnow()
        dt, status = self.calendar.parseDT(argument, sourceTime=now)
        if not status.hasDateOrTime:
            raise commands.BadArgument('invalid time provided, try e.g. "tomorrow" or "3 days"')

        if not status.hasTime:
            # replace it with the current time
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

        self.dt = dt
        self._past = dt < now

    @classmethod
    async def convert(cls, ctx, argument):
        return cls(argument, now=ctx.message.created_at)

class Time(HumanTime):
    def __init__(self, argument, *, now=None):
        try:
            o = ShortTime(argument, now=now)
        except Exception as e:
            super().__init__(argument)
        else:
            self.dt = o.dt
            self._past = False

def parse_timedelta(
    argument: str,
    *,
    maximum: Optional[timedelta] = None,
    minimum: Optional[timedelta] = None,
    allowed_units: Optional[List[str]] = None,
) -> Optional[timedelta]:
    matches = TIME_RE.match(argument)
    allowed_units = allowed_units or ["weeks", "days", "hours", "minutes", "seconds"]
    if matches:
        params = {k: int(v) for k, v in matches.groupdict().items() if v is not None}
        for k in params.keys():
            if k not in allowed_units:
                raise commands.BadArgument(
                    ("`{unit}` is not a valid unit of time for this command").format(unit=k)
                )
        if params:
            delta = timedelta(**params)
            if maximum and maximum < delta:
                raise commands.BadArgument(("This amount of time is too large for this command. (Maximum: {maximum})").format(maximum=humanize_timedelta(timedelta=maximum)))
            if minimum and delta < minimum:
                raise commands.BadArgument(("This amount of time is too small for this command. (Minimum: {minimum})").format(minimum=humanize_timedelta(timedelta=minimum)))
            return delta
    return None

def humanize_timedelta(*, timedelta: Optional[timedelta] = None, seconds: Optional[SupportsInt] = None) -> str:
    try:
        obj = seconds if seconds is not None else timedelta.total_seconds()
    except AttributeError:
        raise ValueError("You must provide either a timedelta or a number of seconds")

    seconds = int(obj)
    periods = [
        (("year"), ("years"), 60 * 60 * 24 * 365),
        (("month"), ("months"), 60 * 60 * 24 * 30),
        (("day"), ("days"), 60 * 60 * 24),
        (("hour"), ("hours"), 60 * 60),
        (("minute"), ("minutes"), 60),
        (("second"), ("seconds"), 1),
    ]

    strings = []
    for period_name, plural_period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 0:
                continue
            unit = plural_period_name if period_value > 1 else period_name
            strings.append(f"{period_value} {unit}")

    return human_join(strings, final='and')

def short_humanize_timedelta(*, timedelta: Optional[timedelta] = None, seconds: Optional[SupportsInt] = None) -> str:
    try:
        obj = seconds if seconds is not None else timedelta.total_seconds()
    except AttributeError:
        raise ValueError("You must provide either a timedelta or a number of seconds")

    seconds = int(obj)
    periods = [
        (("y"), 60 * 60 * 24 * 365),
        (("month"), 60 * 60 * 24 * 30),
        (("d"), 60 * 60 * 24),
        (("h"), 60 * 60),
        (("m"), 60),
        (("s"), 1),
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 0:
                continue
            unit = period_name
            strings.append(f"{period_value} {unit}")

    return human_join(strings, final='and')

def human_timedelta(dt, *, source=None, accuracy=3, brief=False, suffix=True):
    """
    Get locale aware human timedelta representation.
    """
    now = source or discord.utils.utcnow()
    now = now.replace(microsecond=0)
    dt = dt.replace(microsecond=0)
    if dt > now:
        delta = relativedelta(dt, now)
        suffix = ''
    else:
        delta = relativedelta(now, dt)
        suffix = ' ago' if suffix else ''
    attrs = [
        ('year', 'y'),
        ('month', 'mo'),
        ('day', 'd'),
        ('hour', 'h'),
        ('minute', 'm'),
        ('second', 's'),
    ]
    output = []
    for attr, brief_attr in attrs:
        elem = getattr(delta, attr + 's')
        if not elem:
            continue
        if elem <= 0:
            continue
        if brief:
            output.append(f'{elem}{brief_attr}')
        else:
            output.append(format(plural(elem), attr))
    if accuracy is not None:
        output = output[:accuracy]
    if len(output) == 0:
        return 'now'
    else:
        if not brief:
            return human_join(output, final='and') + suffix
        else:
            return ' '.join(output) + suffix

class UserFriendlyTime(commands.Converter):
    """That way quotes aren't absolutely necessary."""
    def __init__(self, converter=None, *, default=None):
        if isinstance(converter, type) and issubclass(converter, commands.Converter):
            converter = converter()

        if converter is not None and not isinstance(converter, commands.Converter):
            raise TypeError('commands.Converter subclass necessary.')

        self.converter = converter
        self.default = default

    async def check_constraints(self, ctx, now, remaining):
        if self.dt < now:
            raise ArgumentBaseError(message='This time is in the past.')

        if not remaining:
            if self.default is None:
                raise ArgumentBaseError(message='Missing argument after the time.')
            remaining = self.default

        if self.converter is not None:
            self.arg = await self.converter.convert(ctx, remaining)
        else:
            self.arg = remaining
        return self

    def copy(self):
        cls = self.__class__
        obj = cls.__new__(cls)
        obj.converter = self.converter
        obj.default = self.default
        return obj

    async def convert(self, ctx, argument):
        # Create a copy of ourselves to prevent race conditions from two
        # events modifying the same instance of a converter
        result = self.copy()
        calendar = HumanTime.calendar
        regex = ShortTime.compiled
        now = ctx.message.created_at

        match = regex.match(argument)
        if match is not None and match.group(0):
            data = { k: int(v) for k, v in match.groupdict(default=0).items() }
            remaining = argument[match.end():].strip()
            result.dt = now + relativedelta(**data)
            return await result.check_constraints(ctx, now, remaining)


        # apparently nlp does not like "from now"
        # it likes "from x" in other cases though so let me handle the 'now' case
        if argument.endswith('from now'):
            argument = argument[:-8].strip()

        if argument[0:2] == 'me':
            # starts with "me to", "me in", or "me at "
            if argument[0:6] in ('me to ', 'me in ', 'me at '):
                argument = argument[6:]

        elements = calendar.nlp(argument, sourceTime=now)
        if elements is None or len(elements) == 0:
            raise ArgumentBaseError(message='Invalid time provided, try e.g. "tomorrow" or "3 days".')

        # handle the following cases:
        # "date time" foo
        # date time foo
        # foo date time

        # first the first two cases:
        dt, status, begin, end, dt_string = elements[0]

        if not status.hasDateOrTime:
            raise ArgumentBaseError(message='Invalid time provided, try e.g. "tomorrow" or "3 days".')

        if begin not in (0, 1) and end != len(argument):
            raise ArgumentBaseError(message='Time is either in an inappropriate location, which '
                                       'must be either at the end or beginning of your input, '
                                       'or I just flat out did not understand what you meant. Sorry.')

        if not status.hasTime:
            # replace it with the current time
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

        # if midnight is provided, just default to next day
        if status.accuracy == pdt.pdtContext.ACU_HALFDAY:
            dt = dt.replace(day=now.day + 1)

        result.dt = dt.replace(tzinfo=datetime.timezone.utc)

        if begin in (0, 1):
            if begin == 1:
                # check if it's quoted:
                if argument[0] != '"':
                    raise ArgumentBaseError(message='Expected quote before time input...')

                if not (end < len(argument) and argument[end] == '"'):
                    raise ArgumentBaseError(message='If the time is quoted, you must unquote it.')

                remaining = argument[end + 1:].lstrip(' ,.!')
            else:
                remaining = argument[end:].lstrip(' ,.!')
        elif len(argument) == end:
            remaining = argument[:begin].strip()

        return await result.check_constraints(ctx, now, remaining)