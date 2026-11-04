import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', title: 'Lab · ukdoshi.com', loadComponent: () => import('./pages/home/home') },
  {
    path: 'couch-critics',
    title: 'The Couch Critics · Lab',
    loadComponent: () => import('./pages/couch-critics/couch-critics'),
  },
  { path: '**', redirectTo: '' },
];
