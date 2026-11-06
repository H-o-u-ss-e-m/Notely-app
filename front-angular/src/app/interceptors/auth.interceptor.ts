import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const withToken = auth.token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${auth.token}` } })
    : req;

  return next(withToken).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status !== 401 || req.url.includes('/auth/')) {
        return throwError(() => err);
      }
      return auth.refreshOnce().pipe(
        switchMap(tok =>
          next(req.clone({ setHeaders: { Authorization: `Bearer ${tok}` } }))
        ),
        catchError(e => {
          auth.logout();
          return throwError(() => e);
        })
      );
    })
  );
};
