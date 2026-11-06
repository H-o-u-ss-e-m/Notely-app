import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from '../services/auth.service';

describe('authInterceptor & AuthService.refreshOnce (Mission 5 / Partie 5.8)', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let authService: AuthService;

  beforeEach(() => {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      sessionStorage.clear();
    }
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('ajoute le header Authorization Bearer quand un token est présent', () => {
    authService.setTokensForTest('tok-initial', 'ref-initial');

    http.get('/api/v1/courses/subjects').subscribe();

    const req = httpMock.expectOne('/api/v1/courses/subjects');
    expect(req.request.headers.get('Authorization')).toBe('Bearer tok-initial');
    req.flush([]);
  });

  it('rafraîchit une seule fois (refreshOnce partagé) sur 401 concurrents et rejoue les requêtes', async () => {
    authService.setTokensForTest('expired-tok', 'valid-refresh');

    const p1 = firstValueFrom(http.get('/api/v1/courses/subjects'));
    const p2 = firstValueFrom(http.get('/api/v1/me/export'));

    const req1 = httpMock.expectOne('/api/v1/courses/subjects');
    const req2 = httpMock.expectOne('/api/v1/me/export');

    // Les deux échouent en 401 simultanément
    req1.flush({ detail: 'Expired' }, { status: 401, statusText: 'Unauthorized' });
    req2.flush({ detail: 'Expired' }, { status: 401, statusText: 'Unauthorized' });

    // UNE SEULE requête /auth/refresh doit partir grâce à shareReplay(1)
    const refreshReqs = httpMock.match(r => r.url.includes('/auth/refresh'));
    expect(refreshReqs.length).toBe(1);
    refreshReqs[0].flush({
      access_token: 'fresh-tok-2',
      refresh_token: 'fresh-ref-2',
      user: { id: 'u1', email: 'a@b.c', full_name: 'A', role: 'student' },
    });

    // Les deux requêtes initiales sont rejouées avec 'fresh-tok-2'
    const retry1 = httpMock.expectOne('/api/v1/courses/subjects');
    const retry2 = httpMock.expectOne('/api/v1/me/export');
    expect(retry1.request.headers.get('Authorization')).toBe('Bearer fresh-tok-2');
    expect(retry2.request.headers.get('Authorization')).toBe('Bearer fresh-tok-2');

    retry1.flush([{ id: 's1' }]);
    retry2.flush({ ok: true });

    const [res1, res2] = await Promise.all([p1, p2]);
    expect(res1).toEqual([{ id: 's1' }]);
    expect(res2).toEqual({ ok: true });
  });
});
