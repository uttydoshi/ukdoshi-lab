/** A run as the API returns it (see backend/app/runs.py): numbers only, never a GPS route. */
export interface Run {
  start: string; // ISO 8601 with offset; also the run's id
  time_zone: string | null;
  duration_s: number;
  distance_m: number | null;
  heart_rate: { average: number; minimum: number | null; maximum: number | null } | null;
  splits: { unit: 'km'; seconds: number[] } | null; // whole kilometres, then the last part-kilometre
  elevation_gain_m: number | null;
  temperature_c: number | null;
  humidity_pct: number | null;
  indoor: boolean;
}

export interface RecapLine {
  speaker: 'Minnie' | 'Maverick';
  text: string;
}

export interface Recap {
  run: Run;
  facts: string[];
  lines: RecapLine[];
  model: string;
}

/** 2656 -> '44:16', 3723 -> '1:02:03' (as the recap's facts write it). */
export function clock(seconds: number): string {
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = String(total % 60).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`;
}

export function km(run: Run): string | null {
  return run.distance_m ? (run.distance_m / 1000).toFixed(1) : null;
}

export function pace(run: Run): string | null {
  return run.distance_m ? clock(run.duration_s / (run.distance_m / 1000)) : null;
}

/** Only the whole kilometres: the Watch's last split is the final part-kilometre. */
export function wholeSplits(run: Run): number[] {
  return run.splits && run.distance_m ? run.splits.seconds.slice(0, Math.floor(run.distance_m / 1000)) : [];
}

/** The run's date and time where it happened, e.g. { day: 'Sun 2 Nov', time: '6:40 am', weekday: 'Sunday', hour: 6 }. */
export function when(run: Run) {
  const date = new Date(run.start);
  const zone = run.time_zone ?? undefined;
  const part = (options: Intl.DateTimeFormatOptions) =>
    new Intl.DateTimeFormat('en-AU', { timeZone: zone, ...options }).format(date);
  return {
    day: part({ weekday: 'short', day: 'numeric', month: 'short' }).replace(',', ''),
    time: part({ hour: 'numeric', minute: '2-digit', hour12: true }),
    weekday: part({ weekday: 'long' }),
    hour: Number(part({ hour: 'numeric', hour12: false })) % 24,
  };
}

/** 'Sunday morning run', 'Tuesday treadmill run' (parts of the day as in the recap's facts). */
export function runName(run: Run): string {
  const { weekday, hour } = when(run);
  if (run.indoor) return `${weekday} treadmill run`;
  const partOfDay = hour < 7 ? 'early morning' : hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening';
  return `${weekday} ${partOfDay} run`;
}
