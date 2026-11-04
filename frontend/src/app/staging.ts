import { inject, Injectable } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterStateSnapshot, TitleStrategy } from '@angular/router';

// Which copy of the lab this is, from its address: staging.lab.ukdoshi.com is the test copy.
// Everything that marks staging checks this, so none of it can show on lab.ukdoshi.com.
export const IS_STAGING = location.hostname === 'staging.lab.ukdoshi.com';

// Filled in by the deploy workflow (ng build --define); absent in local builds and tests.
declare const BUILD_COMMIT: string;
declare const BUILD_TIME: string;
export const BUILD =
  typeof BUILD_COMMIT === 'string' ? { commit: BUILD_COMMIT, time: new Date(BUILD_TIME) } : null;

/** Staging tabs: "[Staging]" before the page title, and a favicon with an amber dot. */
@Injectable({ providedIn: 'root' })
export class SiteTitleStrategy extends TitleStrategy {
  private readonly title = inject(Title);

  constructor() {
    super();
    if (IS_STAGING) {
      document.querySelector('link[rel="icon"]')?.setAttribute('href', 'favicon-staging.svg');
    }
  }

  override updateTitle(snapshot: RouterStateSnapshot): void {
    const title = this.buildTitle(snapshot) ?? 'Lab · ukdoshi.com';
    this.title.setTitle(IS_STAGING ? `[Staging] ${title}` : title);
  }
}
