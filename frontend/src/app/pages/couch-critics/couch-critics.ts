import { Component } from '@angular/core';

/** The Couch Critics, for now a placeholder that explains what's coming. */
@Component({
  selector: 'app-couch-critics',
  styles: `
    .cast {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
      gap: 1rem;
      margin: 2rem 0;
    }

    h2 {
      margin: 0 0 0.5rem;
      font-size: 1.5rem;
    }

    .panel p {
      margin: 0;
    }

    .soon {
      display: inline-block;
      padding: 0.2rem 0.65rem;
      border-radius: 999px;
      background: var(--accent-12);
      color: var(--accent);
      font-size: 0.8rem;
      font-weight: 700;
    }
  `,
  template: `
    <article class="card">
      <span class="soon">Being built</span>
      <h1>The Couch Critics</h1>
      <p>
        Every time I go for a run, my two toy poodles stay home on the couch. When I get back, they review it:
        my pace, the hills, my heart rate, and why I didn't take them.
      </p>
      <div class="cast">
        <section class="panel">
          <h2>Minnie</h2>
          <p>The boss. Reads your stats, demands better, and wants the ball thrown. Now.</p>
        </section>
        <section class="panel">
          <h2>Maverick</h2>
          <p>The couch potato. Exhausted by your run without leaving the couch. Wants pats forever.</p>
        </section>
      </div>
      <p>
        Under the hood: each recap comes from my real run data, every LLM call is traced, and evals check that
        the numbers are right and each poodle stays in character.
      </p>
    </article>
  `,
})
export default class CouchCritics {}
