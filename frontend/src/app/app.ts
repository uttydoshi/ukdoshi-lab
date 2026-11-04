import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

/** The lab's frame: a dark top bar, the routed page, and a short footer. */
@Component({
  imports: [RouterLink, RouterOutlet],
  selector: 'app-root',
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }

    header {
      box-sizing: border-box;
      width: calc(100% - 1.5rem);
      max-width: var(--page-width);
      margin: 0.75rem auto 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 0.6rem 1.1rem;
      border-radius: 1rem;
      background: var(--dark);
      box-shadow: 0 8px 24px rgb(26 26 46 / 0.22);
    }

    header a {
      min-height: 44px;
      display: inline-flex;
      align-items: center;
      color: #fff;
      text-decoration: none;
    }

    .brand {
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.2em;
      text-transform: uppercase;
    }

    .home {
      font-size: 0.95rem;
      opacity: 0.85;
    }

    header a:hover {
      text-decoration: underline;
      text-underline-offset: 0.35em;
    }

    header a:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }

    main {
      flex: 1;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      padding: 1.5rem 0.75rem 2rem;
    }

    footer {
      padding: 0 1rem 2rem;
      text-align: center;
      font-size: 0.85rem;
      color: var(--muted);
    }
  `,
  template: `
    <header>
      <a class="brand" routerLink="/">Utty's lab</a>
      <a class="home" href="https://ukdoshi.com">ukdoshi.com →</a>
    </header>
    <main><router-outlet /></main>
    <footer>© 2026 Utkarsh Doshi</footer>
  `,
})
export class App {}
