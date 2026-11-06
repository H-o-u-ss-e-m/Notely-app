import { Injectable } from '@angular/core';
import {
  BehaviorSubject,
  Observable,
  firstValueFrom,
  throwError,
} from 'rxjs';
import { finalize, map, shareReplay, tap } from 'rxjs/operators';
import { ApiService } from './api.service';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<UserProfile | null>(null);
  public currentUser$: Observable<UserProfile | null> = this.currentUserSubject.asObservable();

  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private refreshInFlight$: Observable<string> | null = null;

  constructor(private apiService: ApiService) {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      const storedUser    = sessionStorage.getItem('notely_user');
      const storedAccess  = sessionStorage.getItem('notely_access_token');
      const storedRefresh = sessionStorage.getItem('notely_refresh_token');
      if (storedUser && storedAccess && storedRefresh) {
        try {
          this.currentUserSubject.next(JSON.parse(storedUser));
          this.accessToken  = storedAccess;
          this.refreshToken = storedRefresh;
        } catch {
          this.clearSession();
        }
      }
    }
  }

  // ── Getters ──────────────────────────────────────────────────────────────

  get currentUser(): UserProfile | null { return this.currentUserSubject.value; }
  get isAuthenticated(): boolean { return this.currentUserSubject.value !== null; }
  get token(): string | null { return this.accessToken; }
  get refreshTokenValue(): string | null { return this.refreshToken; }

  setTokensForTest(access: string | null, refresh: string | null) {
    this.accessToken = access;
    this.refreshToken = refresh;
    if (typeof window !== 'undefined' && window.sessionStorage) {
      if (access) sessionStorage.setItem('notely_access_token', access);
      if (refresh) sessionStorage.setItem('notely_refresh_token', refresh);
    }
  }

  // ── Authentification ─────────────────────────────────────────────────────

  async login(email: string, pass: string): Promise<UserProfile> {
    try {
      const res = await firstValueFrom(this.apiService.login(email, pass));
      this._setSession(res);
      return res.user;
    } catch (err: any) {
      throw new Error(err.error?.detail || 'Erreur lors de la connexion au serveur.');
    }
  }

  async register(email: string, pass: string, displayName?: string): Promise<UserProfile> {
    try {
      const res = await firstValueFrom(this.apiService.register(email, pass, displayName));
      this._setSession(res);
      return res.user;
    } catch (err: any) {
      throw new Error(err.error?.detail || "Erreur lors de l'inscription.");
    }
  }

  async logout(): Promise<void> {
    const rt = this.refreshToken;
    this.clearSession();
    if (rt) {
      try {
        await firstValueFrom(this.apiService.logout(rt));
      } catch {
        // Silencieux — session locale déjà nettoyée
      }
    }
  }

  async logoutAll(): Promise<void> {
    try {
      await firstValueFrom(this.apiService.logoutAll());
    } catch {
      // Silencieux
    } finally {
      this.clearSession();
    }
  }

  // ── Refresh réactif partagé sur 401 (Plan v2 §5.8 — NG-1) ─────────────────

  /**
   * Lance au plus UNE requête `/auth/refresh` partagée (`shareReplay(1)`)
   * lorsque plusieurs appels HTTP reçoivent 401 simultanément.
   */
  refreshOnce(): Observable<string> {
    if (this.refreshInFlight$) {
      return this.refreshInFlight$;
    }
    if (!this.refreshToken) {
      return throwError(() => new Error('Aucun refresh token disponible.'));
    }

    this.refreshInFlight$ = this.apiService.refresh(this.refreshToken).pipe(
      tap(res => this._setSession(res)),
      map(res => res.access_token as string),
      shareReplay(1),
      finalize(() => {
        this.refreshInFlight$ = null;
      })
    );

    return this.refreshInFlight$;
  }

  // ── Session ───────────────────────────────────────────────────────────────

  private _setSession(res: any) {
    this.accessToken  = res.access_token;
    this.refreshToken = res.refresh_token;
    if (res.user) {
      this.currentUserSubject.next(res.user);
    }

    if (typeof window !== 'undefined' && window.sessionStorage) {
      if (res.user) {
        sessionStorage.setItem('notely_user', JSON.stringify(res.user));
      }
      sessionStorage.setItem('notely_access_token',  res.access_token);
      sessionStorage.setItem('notely_refresh_token', res.refresh_token);
    }
  }

  clearSession() {
    this.accessToken    = null;
    this.refreshToken   = null;
    this.refreshInFlight$ = null;
    this.currentUserSubject.next(null);

    if (typeof window !== 'undefined' && window.sessionStorage) {
      sessionStorage.removeItem('notely_user');
      sessionStorage.removeItem('notely_access_token');
      sessionStorage.removeItem('notely_refresh_token');
    }
  }
}
