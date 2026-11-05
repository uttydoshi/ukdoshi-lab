import { clock, km, pace, Run, runName, when, wholeSplits } from './runs';

// A made-up run, never real data. Its last split is the final 0.2 km.
const RUN: Run = {
  start: '2026-11-01T06:40:00+11:00',
  time_zone: 'Australia/Sydney',
  duration_s: 2656,
  distance_m: 8200,
  heart_rate: { average: 152, minimum: 98, maximum: 171 },
  splits: { unit: 'km', seconds: [324, 318, 321, 330, 336, 327, 318, 312, 65] },
  elevation_gain_m: 42,
  temperature_c: 18,
  humidity_pct: 65,
  indoor: false,
};

describe('run formatting', () => {
  it('writes times like the recap facts do', () => {
    expect(clock(2656)).toBe('44:16');
    expect(clock(3723)).toBe('1:02:03');
  });

  it('gives distance and pace', () => {
    expect(km(RUN)).toBe('8.2');
    expect(pace(RUN)).toBe('5:24');
  });

  it('leaves out the last part-kilometre', () => {
    expect(wholeSplits(RUN)).toEqual([324, 318, 321, 330, 336, 327, 318, 312]);
  });

  it('names the run by the day and time where it happened', () => {
    expect(when(RUN).day).toBe('Sun 1 Nov');
    expect(runName(RUN)).toBe('Sunday early morning run');
    expect(runName({ ...RUN, indoor: true })).toBe('Sunday treadmill run');
  });
});
