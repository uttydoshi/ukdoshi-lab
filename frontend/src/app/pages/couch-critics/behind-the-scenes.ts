import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Recap, runName, Span, Trace } from './runs';

const KINDS = { data: 'Data', code: 'Code', llm: 'LLM' } as const;

/** 45 -> '45 ms', 420 -> '0.42 s', 12756 -> '12.8 s' */
export function duration(ms: number): string {
  if (ms < 100) return `${ms} ms`;
  return ms < 1000 ? `${(ms / 1000).toFixed(2)} s` : `${(ms / 1000).toFixed(1)} s`;
}

/** 0.024516 -> '$0.025' */
export function dollars(amount: number): string {
  return amount < 0.001 ? 'under $0.001' : `$${amount.toFixed(3)}`;
}

/** Each step after the whole-request one, placed on a timeline running from the request's start to its end. */
export function steps(trace: Trace) {
  const [request, ...rest] = trace.spans;
  const total = (request.end ?? request.start) - request.start || 1;
  return rest.map((span) => ({
    span,
    kind: KINDS[span.kind as keyof typeof KINDS] ?? span.kind,
    time: duration(span.duration_ms ?? 0),
    left: ((span.start - request.start) / total) * 100,
    width: (((span.end ?? span.start) - span.start) / total) * 100,
  }));
}

/** Each Claude call's model, tokens and cost, as recorded on its step. */
export function llmCalls(trace: Trace) {
  return trace.spans
    .filter((s) => s.kind === 'llm' && s.attributes['gen_ai.usage.input_tokens'] !== undefined)
    .map((s: Span) => ({
      name: s.name,
      model: String(s.attributes['gen_ai.response.model']),
      tokensIn: Number(s.attributes['gen_ai.usage.input_tokens']),
      tokensOut: Number(s.attributes['gen_ai.usage.output_tokens']),
      cost: s.attributes['lab.cost_usd'] === undefined ? null : Number(s.attributes['lab.cost_usd']),
      time: duration(s.duration_ms ?? 0),
    }));
}

/** How one recap was made: every step it took, how long each took, and what the Claude call cost. */
@Component({
  selector: 'app-behind-the-scenes',
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

    .eyebrow {
      margin: 0.5rem 0 0.25rem;
      color: var(--muted);
      font-size: 0.9rem;
    }

    .card h1 {
      margin-bottom: 1rem;
    }

    .tiles {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
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

    .panel {
      margin-bottom: 1rem;
      padding: 1rem;
      border: 1px solid var(--border);
      border-radius: 1.25rem;
      background: #fff;
    }

    .head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 0.75rem;
    }

    h2 {
      margin: 0;
      font-family: var(--font-body);
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .head span {
      font-size: 0.8rem;
      color: var(--muted);
    }

    .steps {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    .step {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }

    .title {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .kind {
      flex: none;
      padding: 0.15rem 0.45rem;
      border-radius: 0.4rem;
      font-size: 0.65rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: #e6eef9;
      color: #1f4e8c;
    }

    .name {
      flex: 1;
      font-weight: 600;
    }

    .time {
      font-size: 0.8rem;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }

    .track {
      position: relative;
      height: 0.5rem;
      border-radius: 0.25rem;
      background: #f1eef4;
    }

    .bar {
      position: absolute;
      top: 0;
      bottom: 0;
      min-width: 4px;
      border-radius: 0.25rem;
      background: #5b8bd0;
    }

    .note {
      font-size: 0.8rem;
      color: var(--muted);
    }

    .failed {
      font-weight: 700;
      color: #a3122a;
    }

    .llm .kind {
      background: #f6e3ee;
      color: #8e1257;
    }

    .llm .bar {
      background: var(--accent);
    }

    .code .kind {
      background: #e9f5ee;
      color: #1e5b3a;
    }

    .code .bar {
      background: #2e9a5e;
    }

    .call {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 0.15rem 0.75rem;
      margin: 0.75rem 0 0;
      padding: 0.75rem 0.9rem;
      border-radius: 0.75rem;
      background: var(--dark);
      color: #e7e3ec;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.8rem;
      line-height: 1.6;
    }

    .call dt {
      color: rgb(231 227 236 / 0.7);
    }

    .call dd {
      margin: 0;
      overflow-wrap: anywhere;
    }

    .how {
      font-size: 0.85rem;
      color: var(--muted);
    }
  `,
  template: `
    <article class="card">
      <a class="back" [routerLink]="['/couch-critics/runs', start()]">‹ Recap</a>

      @if (error()) {
        <p role="alert">{{ error() }}</p>
      } @else if (recap(); as recap) {
        <p class="eyebrow">How the recap of your {{ name(recap.run) }} was made</p>
        <h1>Behind the scenes</h1>

        <div class="tiles">
          <div class="tile"><strong>{{ total() }}</strong><span>total time</span></div>
          <div class="tile"><strong>{{ tokens().toLocaleString('en-AU') }}</strong><span>tokens</span></div>
          <div class="tile"><strong>{{ cost() }}</strong><span>cost</span></div>
        </div>

        <section class="panel" aria-labelledby="trace">
          <div class="head">
            <h2 id="trace">Trace</h2>
            <span>0 s to {{ total() }}</span>
          </div>
          <ol class="steps">
            @for (step of steps(); track step.span.span_id) {
              <li class="step" [class]="step.span.kind">
                <div class="title">
                  <span class="kind">{{ step.kind }}</span>
                  <span class="name">{{ step.span.name }}</span>
                  <span class="time">{{ step.time }}</span>
                </div>
                <div class="track" aria-hidden="true">
                  <div class="bar" [style.left.%]="step.left" [style.width.%]="step.width"></div>
                </div>
                @if (step.span.status === 'error') {
                  <span class="note failed">Failed: {{ step.span.attributes['error.type'] }}</span>
                } @else if (step.span.note) {
                  <span class="note">{{ step.span.note }}</span>
                }
              </li>
            }
          </ol>
        </section>

        @for (call of calls(); track $index) {
          <section class="panel" [attr.aria-label]="'The LLM call: ' + call.name">
            <h2>The LLM call</h2>
            <dl class="call">
              <dt>model</dt>
              <dd>{{ call.model }}</dd>
              <dt>tokens</dt>
              <dd>{{ call.tokensIn.toLocaleString('en-AU') }} in · {{ call.tokensOut.toLocaleString('en-AU') }} out</dd>
              @if (call.cost !== null) {
                <dt>cost</dt>
                <dd>{{ dollars(call.cost) }}</dd>
              }
              <dt>time</dt>
              <dd>{{ call.time }}</dd>
            </dl>
          </section>
        }

        <p class="how">
          Every step is recorded as it runs, in the same shape OpenTelemetry uses, and saved with the recap.
          Tokens out include Claude's thinking, which is billed as output.
        </p>
      } @else {
        <p>Fetching the trace…</p>
      }
    </article>
  `,
})
export default class BehindTheScenes {
  /** The run's start time, from the address (couch-critics/runs/:start/behind-the-scenes). */
  readonly start = input.required<string>();

  private readonly http = inject(HttpClient);
  protected readonly recap = signal<Recap | null>(null);
  protected readonly error = signal('');

  protected readonly steps = computed(() => (this.recap() ? steps(this.recap()!.trace) : []));
  protected readonly calls = computed(() => (this.recap() ? llmCalls(this.recap()!.trace) : []));
  protected readonly total = computed(() => duration(this.recap()?.trace.spans[0].duration_ms ?? 0));
  protected readonly tokens = computed(() => this.calls().reduce((sum, c) => sum + c.tokensIn + c.tokensOut, 0));
  protected readonly cost = computed(() => dollars(this.calls().reduce((sum, c) => sum + (c.cost ?? 0), 0)));
  protected readonly dollars = dollars;
  protected readonly name = runName;

  ngOnInit(): void {
    // The run's newest saved recap: the one its recap screen shows.
    this.http.get<Recap>(`/api/recap?start=${encodeURIComponent(this.start())}`).subscribe({
      next: (recap) => this.recap.set(recap),
      error: (e) => this.error.set(e.error?.detail ?? "The trace couldn't be loaded. Try again shortly."),
    });
  }
}
