import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

interface Experiment {
  name: string;
  path: string;
  pitch: string;
  status: string;
}

const EXPERIMENTS: Experiment[] = [
  {
    name: 'The Couch Critics',
    path: '/couch-critics',
    pitch: 'My two toy poodles, Minnie and Maverick, review my runs from the couch.',
    status: 'Being built',
  },
];

/** The lab's front page: what it is, and a card for each experiment. */
@Component({
  imports: [RouterLink],
  selector: 'app-home',
  styles: `
    .experiments {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
      gap: 1rem;
      margin: 2rem 0 0;
      padding: 0;
      list-style: none;
    }

    a.panel {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      height: 100%;
      color: inherit;
      text-decoration: none;
      transition: border-color 0.2s, transform 0.2s;
    }

    a.panel:hover {
      border-color: var(--accent);
      transform: translateY(-2px);
    }

    a.panel:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }

    h2 {
      margin: 0;
      font-size: 1.5rem;
    }

    .status {
      align-self: flex-start;
      padding: 0.2rem 0.65rem;
      border-radius: 999px;
      background: var(--accent-12);
      color: var(--accent);
      font-size: 0.8rem;
      font-weight: 700;
    }

    .panel p {
      margin: 0;
    }

    @media (prefers-reduced-motion: reduce) {
      a.panel {
        transition: none;
      }
    }
  `,
  template: `
    <article class="card">
      <h1>Utty's lab</h1>
      <p>
        Small, useful experiments with AI. Each one traces every LLM call and is checked by evals, so I can
        show not just that it works, but how well, how fast and at what cost.
      </p>
      <ul class="experiments">
        @for (e of experiments; track e.path) {
          <li>
            <a class="panel" [routerLink]="e.path">
              <span class="status">{{ e.status }}</span>
              <h2>{{ e.name }}</h2>
              <p>{{ e.pitch }}</p>
            </a>
          </li>
        }
      </ul>
    </article>
  `,
})
export default class Home {
  protected readonly experiments = EXPERIMENTS;
}
