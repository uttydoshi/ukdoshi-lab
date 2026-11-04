import { DatePipe } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';
import { BUILD, IS_STAGING } from './staging';

/** The lab's frame: a dark top bar, the routed page, and a short footer. */
@Component({
  imports: [DatePipe, RouterLink, RouterOutlet],
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

    /* Staging only: an amber pill beside the brand, so the test copy is never mistaken for live. */
    .staging-badge {
      margin-right: auto;
      padding: 0.2rem 0.55rem;
      border: 1px solid #fcd34d;
      border-radius: 999px;
      background: #fef3c7;
      color: #92400e;
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
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

    .build {
      margin: 0.4rem 0 0;
      font-size: 0.75rem;
    }
  `,
  template: `
    <header>
      <a class="brand" routerLink="/">Utty's lab</a>
      @if (isStaging) {
        <span class="staging-badge" title="This is the test copy of the lab, not lab.ukdoshi.com">Staging</span>
      }
      <a class="home" href="https://ukdoshi.com">ukdoshi.com →</a>
    </header>
    <main><router-outlet /></main>
    <footer>
      © 2026 Utkarsh Doshi
      @if (isStaging) {
        <!-- Lets testers say exactly which version they saw. -->
        <p class="build">
          Staging ·
          @if (build) {
            built from {{ build.commit }} · {{ build.time | date: 'd MMM, HH:mm' }}
          } @else {
            local build
          }
        </p>
      }
    </footer>
  `,
})
export class App {
  protected readonly isStaging = IS_STAGING;
  protected readonly build = BUILD; // staging only: which version testers are looking at
}
