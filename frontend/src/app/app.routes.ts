import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', title: 'Lab · ukdoshi.com', loadComponent: () => import('./pages/home/home') },
  {
    path: 'couch-critics',
    title: 'The Couch Critics · Lab',
    loadComponent: () => import('./pages/couch-critics/couch-critics'),
  },
  {
    path: 'couch-critics/runs/:start',
    title: 'Run recap · The Couch Critics',
    loadComponent: () => import('./pages/couch-critics/run-recap'),
  },
  {
    path: 'couch-critics/runs/:start/behind-the-scenes',
    title: 'Behind the scenes · The Couch Critics',
    loadComponent: () => import('./pages/couch-critics/behind-the-scenes'),
  },
  { path: '**', redirectTo: '' },
];
