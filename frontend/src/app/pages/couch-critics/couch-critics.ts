import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { clock, km, pace, Run, runName, when } from './runs';

/** The Couch Critics: your runs, newest first. Each one opens Minnie and Maverick's recap. */
@Component({
  selector: 'app-couch-critics',
  imports: [RouterLink],
  styles: `
    .intro {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }

    .intro p {
      margin: 0;
    }

    .avatars {
      display: flex;
    }

    .avatar {
      width: 2rem;
      height: 2rem;
      border-radius: 50%;
      display: grid;
      place-items: center;
      font-size: 0.8rem;
      font-weight: 700;
      border: 2px solid #fff;
    }

    .avatar + .avatar {
      margin-left: -0.5rem;
    }

    .minnie {
      background: #f2c4a0;
      color: #5a2e12;
    }

    .maverick {
      background: #c9ccd8;
      color: var(--text);
    }

    a {
      color: inherit;
      text-decoration: none;
    }

    .latest {
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
      padding: 1.25rem;
      border: 1px solid var(--border);
      border-radius: 1.25rem;
      background: #fff;
      box-shadow: 0 6px 18px rgb(26 26 46 / 0.06);
    }

    .latest:hover,
    .earlier a:hover {
      border-color: var(--accent);
    }

    .latest:focus-visible,
    .earlier a:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }

    .when {
      font-size: 0.85rem;
      color: var(--muted);
    }

    .name {
      font-size: 1.25rem;
      font-weight: 700;
    }

    .stats {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem 1.1rem;
      color: var(--muted);
    }

    .stats strong {
      color: var(--text);
      font-size: 1.1rem;
    }

    .read {
      font-weight: 600;
      color: var(--accent);
    }

    h2 {
      margin: 2rem 0.25rem 0.75rem;
      font-family: var(--font-body);
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .earlier {
      margin: 0;
      padding: 0;
      list-style: none;
      border: 1px solid var(--border);
      border-radius: 1.25rem;
      background: #fff;
      overflow: hidden;
    }

    .earlier li + li {
      border-top: 1px solid var(--border);
    }

    .earlier a {
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
      min-height: 44px;
      padding: 0.85rem 1rem;
      border: 1px solid transparent;
    }

    .earlier .name {
      font-size: 1rem;
      font-weight: 600;
    }
  `,
  template: `
    <article class="card">
      <h1>The Couch Critics</h1>
      <div class="intro">
        <div class="avatars" aria-hidden="true">
          <span class="avatar minnie">Mi</span>
          <span class="avatar maverick">Ma</span>
        </div>
        <p>My runs, reviewed by Minnie and Maverick, who stayed home on the couch.</p>
      </div>

      @if (error()) {
        <p role="alert">{{ error() }}</p>
      } @else if (!runs()) {
        <p>Fetching the runs…</p>
      } @else if (latest(); as run) {
        <a class="latest" [routerLink]="['runs', run.start]">
          <span class="when">{{ day(run) }}</span>
          <span class="name">{{ name(run) }}</span>
          <span class="stats">
            @if (km(run)) {
              <span><strong>{{ km(run) }}</strong> km</span>
            }
            <span><strong>{{ clock(run.duration_s) }}</strong></span>
            @if (pace(run)) {
              <span><strong>{{ pace(run) }}</strong> /km</span>
            }
          </span>
          <span class="read">Read the recap ›</span>
        </a>

        @if (earlier().length) {
          <h2>Earlier</h2>
          <ul class="earlier">
            @for (run of earlier(); track run.start) {
              <li>
                <a [routerLink]="['runs', run.start]">
                  <span class="name">{{ name(run) }}</span>
                  <span class="when">{{ summary(run) }}</span>
                </a>
              </li>
            }
          </ul>
        }
      } @else {
        <p>No runs yet. Import some from Apple Health (see the README).</p>
      }
    </article>
  `,
})
export default class CouchCritics {
  protected readonly runs = signal<Run[] | null>(null);
  protected readonly error = signal('');
  protected readonly latest = computed(() => this.runs()?.[0]);
  protected readonly earlier = computed(() => this.runs()?.slice(1) ?? []);

  protected readonly clock = clock;
  protected readonly km = km;
  protected readonly pace = pace;
  protected readonly name = runName;

  constructor() {
    inject(HttpClient)
      .get<{ runs: Run[] }>('/api/runs')
      .subscribe({
        next: (body) => this.runs.set(body.runs),
        error: () => this.error.set("The runs couldn't be loaded. Try again shortly."),
      });
  }

  protected day(run: Run): string {
    const { day, time } = when(run);
    return `${day} · ${time}`;
  }

  protected summary(run: Run): string {
    const parts = [when(run).day];
    if (km(run)) parts.push(`${km(run)} km`);
    if (pace(run)) parts.push(`${pace(run)} /km`);
    return parts.join(' · ');
  }
}
