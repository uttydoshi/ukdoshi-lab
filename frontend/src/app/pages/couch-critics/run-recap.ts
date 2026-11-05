import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { clock, km, pace, Recap, RecapLine, Run, runName, when, wholeSplits } from './runs';

/** One run: its numbers, a pace-per-km chart, and Minnie and Maverick's recap as a chat. */
@Component({
  selector: 'app-run-recap',
  imports: [RouterLink],
  styles: `
    .back {
      display: inline-flex;
      align-items: center;
      min-height: 44px;
      color: var(--muted);
      font-weight: 600;
      text-decoration: none;
    }

    .when {
      margin: 0.5rem 0 0.25rem;
      color: var(--muted);
      font-size: 0.9rem;
    }

    .card h1 {
      margin-bottom: 1rem;
    }

    .tiles {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(5.5rem, 1fr));
      gap: 0.5rem;
      margin-bottom: 1.25rem;
    }

    .tile {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 0.65rem 0.5rem;
      border-radius: 0.9rem;
      background: var(--dark);
      color: #fff;
    }

    .tile strong {
      font-size: 1.2rem;
    }

    .tile span {
      font-size: 0.75rem;
      color: rgb(255 255 255 / 0.75);
    }

    h2 {
      margin: 0 0 0.75rem;
      font-family: var(--font-body);
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .chart {
      margin-bottom: 1.25rem;
    }

    /* One row per kilometre: its number, a bar (faster is longer) and its time, so short runs leave no gaps. */
    .bars {
      display: grid;
      gap: 4px;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    .bar {
      display: grid;
      grid-template-columns: 1.5rem 1fr 2.75rem;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.8rem;
    }

    .km {
      text-align: right;
      color: var(--muted);
    }

    .fill {
      display: block;
      height: 0.9rem;
      border-radius: 5px;
      background: #e4c2d5;
    }

    .bar.fastest .fill {
      background: var(--accent);
    }

    .bar.slowest .fill {
      background: #9a97a8;
    }

    .time {
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      color: var(--text);
    }

    .hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip-path: inset(50%);
      white-space: nowrap;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 0.25rem 1rem;
      margin-top: 0.5rem;
      font-size: 0.8rem;
      color: var(--muted);
    }

    .legend span::before {
      content: '';
      display: inline-block;
      width: 0.6rem;
      height: 0.6rem;
      margin-right: 0.35rem;
      border-radius: 2px;
      background: var(--accent);
    }

    .legend .slow::before {
      background: #9a97a8;
    }

    .chat {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }

    .line {
      display: flex;
      align-items: flex-end;
      gap: 0.6rem;
    }

    .line.maverick {
      flex-direction: row-reverse;
    }

    .avatar {
      flex: none;
      width: 2.25rem;
      height: 2.25rem;
      border-radius: 50%;
      display: grid;
      place-items: center;
      font-size: 0.8rem;
      font-weight: 700;
      background: #f2c4a0;
      color: #5a2e12;
    }

    .maverick .avatar {
      background: #c9ccd8;
      color: var(--text);
    }

    .bubble {
      max-width: 34rem;
      padding: 0.75rem 0.9rem;
      border: 1px solid var(--border);
      border-radius: 1.1rem 1.1rem 1.1rem 0.25rem;
      background: #fff;
    }

    .maverick .bubble {
      border-radius: 1.1rem 1.1rem 0.25rem 1.1rem;
    }

    .who {
      display: block;
      font-size: 0.75rem;
      font-weight: 700;
      color: #8a4a1f;
    }

    .maverick .who {
      color: #3f4458;
    }

    .bubble p {
      margin: 0.15rem 0 0;
      color: var(--text);
      line-height: 1.5;
    }

    .again {
      min-height: 48px;
      padding: 0 1.25rem;
      border: 1px solid var(--border);
      border-radius: 0.9rem;
      background: #fff;
      color: var(--text);
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }

    .again:disabled {
      cursor: wait;
      opacity: 0.6;
    }

    .again:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }
  `,
  template: `
    <article class="card">
      <a class="back" routerLink="/couch-critics">‹ Runs</a>

      @if (run(); as run) {
        <p class="when">{{ header(run) }}</p>
        <h1>{{ name(run) }}</h1>

        <div class="tiles">
          @if (km(run)) {
            <div class="tile"><strong>{{ km(run) }}</strong><span>km</span></div>
          }
          <div class="tile"><strong>{{ clock(run.duration_s) }}</strong><span>time</span></div>
          @if (pace(run)) {
            <div class="tile"><strong>{{ pace(run) }}</strong><span>avg /km</span></div>
          }
          @if (run.heart_rate) {
            <div class="tile"><strong>{{ run.heart_rate.average }}</strong><span>avg bpm</span></div>
          }
        </div>

        @if (bars().length > 1) {
          <section class="chart">
            <h2>Pace per km</h2>
            <ol class="bars">
              @for (bar of bars(); track bar.km) {
                <li class="bar" [class.fastest]="bar.fastest" [class.slowest]="bar.slowest">
                  <span class="km"><span class="hidden">Kilometre </span>{{ bar.km }}</span>
                  <span><span class="fill" [style.width.%]="bar.width"></span></span>
                  <span class="time">{{ bar.pace }}</span>
                </li>
              }
            </ol>
            <div class="legend" aria-hidden="true">
              <span>Fastest: km {{ fastest().km }}, {{ fastest().pace }}</span>
              @if (slowest(); as slow) {
                <span class="slow">Slowest: km {{ slow.km }}, {{ slow.pace }}</span>
              }
            </div>
          </section>
        }
      }

      <section aria-label="Recap" aria-live="polite">
        @if (recapError()) {
          <p role="alert">{{ recapError() }}</p>
        } @else if (!recap()) {
          <p>Minnie is reading your stats…</p>
        } @else {
          <div class="chat">
            @for (line of recap()!.lines; track $index) {
              <div class="line" [class.maverick]="line.speaker === 'Maverick'">
                <span class="avatar" aria-hidden="true">{{ initials(line) }}</span>
                <div class="bubble">
                  <span class="who">{{ line.speaker }}</span>
                  <p>{{ line.text }}</p>
                </div>
              </div>
            }
          </div>
        }
        <button type="button" class="again" (click)="loadRecap(true)" [disabled]="loading()">Another take</button>
      </section>
    </article>
  `,
})
export default class RunRecap {
  /** The run's start time, from the address (couch-critics/runs/:start). */
  readonly start = input.required<string>();

  private readonly http = inject(HttpClient);
  protected readonly run = signal<Run | null>(null);
  protected readonly recap = signal<Recap | null>(null);
  protected readonly recapError = signal('');
  protected readonly loading = signal(false);

  protected readonly clock = clock;
  protected readonly km = km;
  protected readonly pace = pace;
  protected readonly name = runName;

  /** Faster kilometres get longer bars. Each bar's time is written beside it. */
  protected readonly bars = computed(() => {
    const run = this.run();
    const times = run ? wholeSplits(run) : [];
    const fastest = Math.min(...times);
    const slowest = Math.max(...times);
    return times.map((s, i) => ({
      km: i + 1,
      pace: clock(s),
      fastest: s === fastest,
      slowest: s === slowest && slowest !== fastest,
      width: slowest === fastest ? 80 : 40 + ((slowest - s) / (slowest - fastest)) * 60,
    }));
  });
  protected readonly fastest = computed(() => this.bars().find((b) => b.fastest)!);
  protected readonly slowest = computed(() => this.bars().find((b) => b.slowest));

  ngOnInit(): void {
    this.http.get<{ runs: Run[] }>('/api/runs').subscribe({
      next: (body) => this.run.set(body.runs.find((r) => r.start === this.start()) ?? null),
    });
    this.loadRecap();
  }

  /** The run's saved recap, or (when there's none, or for "Another take") a fresh one from Claude: a few
   *  seconds, and different every time. */
  protected loadRecap(fresh = false): void {
    this.loading.set(true);
    this.recapError.set('');
    this.recap.set(null);
    // encodeURIComponent, not HttpParams: the start time's "+" must reach the API as "+", not a space.
    const url = `/api/recap?start=${encodeURIComponent(this.start())}${fresh ? '&fresh=true' : ''}`;
    this.http.get<Recap>(url).subscribe({
      next: (recap) => {
        this.recap.set(recap);
        this.run.set(recap.run);
        this.loading.set(false);
      },
      error: (e) => {
        this.recapError.set(e.error?.detail ?? "The recap couldn't be written. Try again shortly.");
        this.loading.set(false);
      },
    });
  }

  protected header(run: Run): string {
    const { day, time } = when(run);
    const parts = [day, time];
    if (run.temperature_c !== null && !run.indoor) parts.push(`${Math.round(run.temperature_c)}°C`);
    return parts.join(' · ');
  }

  protected initials(line: RecapLine): string {
    return line.speaker === 'Minnie' ? 'Mi' : 'Ma';
  }
}
