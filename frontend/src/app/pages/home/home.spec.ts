import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import Home from './home';

describe('Home', () => {
  it('lists The Couch Critics with a link to it', async () => {
    await TestBed.configureTestingModule({ imports: [Home], providers: [provideRouter([])] }).compileComponents();
    const fixture = TestBed.createComponent(Home);
    await fixture.whenStable();
    const card = (fixture.nativeElement as HTMLElement).querySelector('.experiments a');
    expect(card?.textContent).toContain('The Couch Critics');
    expect(card?.getAttribute('href')).toBe('/couch-critics');
  });
});
